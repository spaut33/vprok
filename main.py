import mailbox
import bs4
import re
import psycopg2
import os


DB_NAME = os.environ.get('DB_NAME')
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')
HOSTNAME = os.environ.get('HOSTNAME')


conn = psycopg2.connect(dbname=DB_NAME, user=USERNAME,
                        password=PASSWORD, host=HOSTNAME)

# https://stackoverflow.com/questions/65882780/write-html-file-from-mbox

HTML_FOOTER = "</body></html>"


def html_parser(content):

    soup = bs4.BeautifulSoup(content, 'lxml')
    # Order number
    h1 = soup.find('h1').contents[0]
    order_number = re.findall(r'\d+', h1)
    # Order total
    total_price = re.findall(r'^.*с учетом доставки:.[\s\S]*>(\d.*\.\d+)&.*$',
                             content, re.MULTILINE)
    # print(order_number[0])
    # print(total_price[0].replace('&nbsp;', ''))

    # Items table
    items_table = soup.find('table', {'class': 'table__table'})
    if items_table:
        pass
    else:
        items_table = soup.find('table', {'style': lambda s: s and
                                'font-size:13px;line-height:15px;' in s})
    table_length = len(items_table.find_all('tr')) - 1
    # Iterate over tables to get all items from the order
    order_items_list = []
    for row in items_table.find_all('tr')[1:table_length]:
        col = row.find_all('td')
        if len(col) == 4 or len(col) == 5:
            item_features = {}
            item_name = col[0].get_text(strip=True)
            item_weight = re.sub(r'[^0-9\.]', '', col[1].get_text(strip=True))
            item_price = re.sub(r'[^0-9\.]', '',
                                col[2].get_text(strip=True))[:-1]
            if len(col) == 4:
                total_price = re.sub(r'[^0-9\.]', '',
                                     col[3].get_text(strip=True))[:-1]
            else:
                total_price = re.sub(r'[^0-9\.]', '',
                                     col[4].get_text(strip=True))[:-1]
            if 'Вес заказа' in item_name:
                continue
            elif item_price and total_price:
                item_features[item_name] = [item_weight,
                                            item_price,
                                            total_price]
                order_items_list.append(item_features)
    return order_number[0], order_items_list


def mailbox_parser(mbox_filename):
    order_content = []
    all_orders = []
    mbox = mailbox.mbox(mbox_filename)
    for message in mbox:

        mess_from = message['from']
        subject = message['subject']
        time_received = message['date']
        fname = subject + " " + time_received
        fname = fname.replace('/', '-')

        if message.is_multipart():
            contents_text = []
            contents_html = []
            for part in message.walk():
                maintype = part.get_content_maintype()
                subtype = part.get_content_subtype()
                if maintype == 'multipart' or maintype == 'message':
                    # Reject containers
                    continue
                if subtype == 'html':
                    enc = part.get_charsets()
                    if enc[0] is not None:
                        contents_html.append(part.get_payload(decode=True).decode(enc[0]))
                    else:
                        contents_html.append(part.get_payload(decode=False))
                elif subtype == 'text':
                    contents_text.append(part.get_payload(decode=False))
                else:       # I will use this to process attachmnents in the future
                    continue

            if len(contents_html) > 0:
                if len(contents_html) > 1:
                    print('multiple html')      # This hasn't happened yet
                content = '\n\n'.join(contents_html)
                order_number, order_item_list = html_parser(content)
            order_content = [time_received, order_number, order_item_list]
        else:
            content = message.get_payload(decode=False)
            content = content.replace('\\n', '<br/>')
            content = content.replace('=\n', '<br/>')
            content = content.replace('\n', '<br/>')
            content = content.replace('=20', '')
            html_header = f""" <!DOCTYPE html>
            <html>
            <head>
            <title>{fname}</title>
            </head>
            <body>"""
            content = (html_header + '<br/>' +
                       'From: ' + mess_from + '<br/>' +
                       'Subject: ' + subject + '<br/>' +
                       'Received: ' + time_received + '<br/><br/>' +
                       content + HTML_FOOTER)
        all_orders.append(order_content)
        # print(time_received)
        # print('--------------')
    return all_orders


mbox_filename = './mbox/Перекресток-выполнен.mbox'

all_orders = mailbox_parser(mbox_filename)


# with open('all-orders.txt', 'w') as f:
#     for item in all_orders:
#         f.write('%s\n' % item)
# end open file
