import mailbox
import bs4
import re
import psycopg2
import config


# https://stackoverflow.com/questions/65882780/write-html-file-from-mbox

HTML_FOOTER = "</body></html>"


def db_create_tabe():
    conn = psycopg2.connect(dbname=config.DB_NAME, user=config.USERNAME,
                            password=config.PASSWORD, host=config.HOSTNAME)
    cursor = conn.cursor()
    cursor.execute(config.create_table_sql)
    conn.commit()
    conn.close()


def db_insert_items(items_to_insert):
    conn = psycopg2.connect(dbname=config.DB_NAME, user=config.USERNAME,
                            password=config.PASSWORD, host=config.HOSTNAME)
    cursor = conn.cursor()
    # cursor.execute('INSERT INTO public.items (order_id, order_date, item_name, item_qnty, item_price_1, item_price)
    #                 VALUES (1,
    #                         2,
    #                         3,
    #                         4,
    #                         5,
    #                         6) ON CONFLICT (order_id) DO NOTHING;')
    query_list = []
    for order in items_to_insert:
        for item in order[2]:
            item_qnty = list(item.values())[0][0]
            item_price_1 = list(item.values())[0][1]
            item_price = list(item.values())[0][2]
            query_list.append((order[1], order[0], list(item.keys())[0], item_qnty, item_price_1, item_price))
    query = """INSERT INTO public.items
               (order_id, order_date, item_name, item_qnty, item_price_1, item_price)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (order_id, item_name) DO NOTHING;
            """
    try:
        cursor.executemany(query, query_list)
        conn.commit()
    except:
        conn.rollback()


def html_parser(content):
    table_length = 0
    soup = bs4.BeautifulSoup(content, 'lxml')
    # Order number
    h1 = soup.find('h1').get_text()
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
    if items_table:
        table_length = len(items_table.find_all('tr')) - 1
    # Iterate over tables to get all items from the order
    order_items_list = []
    if table_length > 0:
        for row in items_table.find_all('tr')[1:table_length]:
            col = row.find_all('td')
            if len(col) == 4 or len(col) == 5:
                item_features = {}
                item_name = col[0].get_text(strip=True)
                if item_name != '':
                    try:
                        item_weight = re.findall(r'\d*\.\d+|\d+', col[1].contents[0].replace(' ', ''))[0]
                    except IndexError:
                        item_weight = 0
                    try:
                        item_price = re.findall(r'\d*\.\d+|\d+', col[2].contents[0].replace(' ', ''))[0]
                    except (IndexError, TypeError):
                        item_price = 0
                    if len(col) == 4:
                        try:
                            total_price = re.findall(r'\d*\.\d+|\d+', col[3].contents[0].replace(' ', ''))[0]
                        except IndexError:
                            total_price = 0
                    else:
                        try:
                            total_price = re.findall(r'\d*\.\d+|\d+', col[4].contents[0].replace(' ', ''))[0]
                        except IndexError:
                            total_price = 0
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

# Just for test purposes
# Read the lists from the text file
# with open('all-orders.txt', 'r') as f:
#     all_orders = []
#     for line in f:
#         line = eval(line)
#         all_orders.append(line)

db_insert_items(all_orders)

# Just to test purposes
# Save the lists into the text file
# with open('all-orders.txt', 'w') as f:
#     for item in all_orders:
#         f.write('%s\n' % item)
