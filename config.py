import os


create_table_sql = """CREATE TABLE IF NOT EXISTS public.items
(
    order_id integer NOT NULL,
    order_date timestamp with time zone,
    item_name character varying(255) COLLATE pg_catalog."default" NOT NULL,
    item_qnty numeric(10,2),
    item_price_1 numeric(10,2),
    item_price numeric(10,2),
    CONSTRAINT vprok_items PRIMARY KEY (order_id, item_name)
)
                   """
DB_NAME = os.environ.get('DB_NAME')
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')
HOSTNAME = os.environ.get('HOSTNAME')
