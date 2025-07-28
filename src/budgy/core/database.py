import datetime
import logging
from pathlib import Path
from typing import List, Dict, Optional

# SQLCipher is required for security - fail if not available
try:
    import sqlcipher3
except ImportError:
    raise ImportError(
        "SQLCipher is required but not installed. "
        "Install with: pip install sqlcipher3-binary"
    )
class BudgyDatabase(object):
    TXN_TABLE_NAME = 'transactions'
    CATEGORY_TABLE_NAME = 'categories'
    CATEGORY_RULES_TABLE_NAME = 'cat_rules'
    DEFAULT_CATEGORY = 'No Category'
    EMPTY_SUBCATEGORY = ''
    NON_EXPENSE_TYPE = 0
    ONE_TIME_EXPENSE_TYPE = 1
    RECURRING_EXPENSE_TYPE = 2
    connection = None
    
    def __init__(self, path, encryption_key: Optional[str] = None):
        """
        Initialize encrypted database.
        
        Args:
            path: Path to database file
            encryption_key: Hex-encoded encryption key for SQLCipher
                          If None, will prompt for master password
        """
        self.db_path = Path(path)
        self.encryption_key = encryption_key
        self._open_database()
    def table_exists(self, table_name):
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
        result = self.execute(sql, (table_name,))
        rows = result.fetchall()
        return len(rows) > 0
    def index_exists(self, index_name):
        sql = "SELECT name FROM sqlite_master WHERE type='index' AND name=?;"
        result = self.execute(sql, (index_name,))
        rows = result.fetchall()
        return len(rows) > 0
    def _create_txn_table_if_missing(self):
        table_name = self.TXN_TABLE_NAME
        if not self.table_exists(table_name):
            logging.info(f'Creating table: {table_name}')
            sql = f'CREATE TABLE IF NOT EXISTS {table_name} (' \
                  f'fitid INTEGER PRIMARY KEY AUTOINCREMENT, ' \
                  f'account TEXT, ' \
                  f'type TEXT, ' \
                  f'posted TEXT, ' \
                  f'amount FLOAT, ' \
                  f'name TEXT, ' \
                  f'memo TEXT, ' \
                  f'category INT DEFAULT 1, ' \
                  f'checknum TEXT' \
                  f');'
            logging.debug(f'Executing SQL: {sql}')
            result = self.execute(sql)
            logging.debug(f'Create Table Result: {result}')
            # Create index on content fields for duplicate detection
            sql = f'CREATE INDEX content_lookup ON {table_name} (account, posted, amount, name, memo, type);'
            result = self.execute(sql)
            logging.debug(f'Create Unique Index: {result}')
    def _create_rules_table_if_missing(self):
        table_name = self.CATEGORY_RULES_TABLE_NAME
        if not self.table_exists(table_name):
            logging.info(f'Creating table: {table_name}')
            sql = f'CREATE TABLE IF NOT EXISTS {table_name} (' \
                   f'id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
                   f'pattern TEXT, ' \
                   f'category TEXT, ' \
                   f'subcategory TEXT ' \
                   f');'
            logging.debug(f'Executing SQL: {sql}')
            result = self.execute(sql)
            logging.debug(f'Create Table Result: {result}')
    def _create_category_table_if_missing(self):
        table_name = self.CATEGORY_TABLE_NAME
        if not self.table_exists(table_name):
            logging.info(f'Creating table: {self.CATEGORY_TABLE_NAME}')
            sql = f'CREATE TABLE IF NOT EXISTS {table_name} (' \
                  f'id INTEGER PRIMARY KEY AUTOINCREMENT, ' \
                  f'name TEXT, ' \
                  f'subcategory TEXT, ' \
                  f'expense_type INTEGER DEFAULT 0' \
                  f');'
            result = self.execute(sql)
            logging.debug(f'Create Table Result: {result}')
            sql = f'CREATE UNIQUE INDEX category_full ON {table_name} (name, subcategory);'
            result = self.execute(sql)
            logging.debug(f'Create Unique Index: {result}')
            # load default values
            ### expense_type:
            # 0: not an expense
            # 1: one-time expense (like a car purchase)
            # 2: recurring expense (expenses that will continue in retirement)
            default_categories = [
                (self.DEFAULT_CATEGORY, self.EMPTY_SUBCATEGORY, 0),
                ('Expense', self.EMPTY_SUBCATEGORY, 2),
                ('Expense', 'Check', 2),
                ('Auto', self.EMPTY_SUBCATEGORY, 2),
                ('Auto', 'Gas', 2),
                ('Auto', 'Purchase', 1),
                ('Auto', 'Repairs', 2),
                ('Auto', 'Service', 2),
                ('Auto', 'DMV', 2),
                ('Cash Withdrawal', self.EMPTY_SUBCATEGORY, 2),
                ('Clothing', self.EMPTY_SUBCATEGORY, 2),
                ('Dry Cleaning', self.EMPTY_SUBCATEGORY, 2),
                ('Education', self.EMPTY_SUBCATEGORY, 2),
                ('Education', 'Books', 2),
                ('Education', 'College', 1),
                ('Education', 'Professional', 1),
                ('Education', 'Tuition', 1),
                ('Education', 'Post Secondary', 1),
                ('Entertainment', self.EMPTY_SUBCATEGORY, 2),
                ('Entertainment', 'Drinks', 2),
                ('Entertainment', 'Coffee', 2),
                ('Entertainment', 'Dining', 2),
                ('Entertainment', 'Movies', 2),
                ('Entertainment', 'Video Streaming', 2),
                ('Groceries / Food', self.EMPTY_SUBCATEGORY, 2),
                ('Household', self.EMPTY_SUBCATEGORY, 2),
                ('Household', 'Cleaning', 2),
                ('Household', 'Furniture', 2),
                ('Household', 'Gardener', 2),
                ('Household', 'Pool Maintenance', 2),
                ('Household', 'Remodel', 1),
                ('Household', 'Rent', 2),
                ('Household', 'Repairs', 2),
                ('Insurance', self.EMPTY_SUBCATEGORY, 2),
                ('Insurance', 'Auto', 2),
                ('Insurance', 'Home', 2),
                ('Insurance', 'Life', 2),
                ('Insurance', 'Medical', 2),
                ('Postage / Shipping', self.EMPTY_SUBCATEGORY, 2),
                ('Recreation', self.EMPTY_SUBCATEGORY, 2),
                ('Recreation', 'Golf', 2),
                ('Recreation', 'Camping', 2),
                ('Recreation', 'Hobbies', 2),
                ('Rideshare', self.EMPTY_SUBCATEGORY, 2),
                ('Taxes', self.EMPTY_SUBCATEGORY, 1),
                ('Taxes', 'Federal', 1),
                ('Taxes', 'State', 1),
                ('Travel', self.EMPTY_SUBCATEGORY, 2),
                ('Travel', 'Hotel', 2),
                ('Travel', 'Tours', 2),
                ('Travel', 'Transportation (air, sea, rail)', 2),
                ('Utilities', self.EMPTY_SUBCATEGORY, 2),
                ('Utilities', 'Cable', 2),
                ('Utilities', 'Gas / Electric', 2),
                ('Utilities', 'Internet', 2),
                ('Utilities', 'Phone', 2),
                ('Utilities', 'Water', 2),
                ('Income', self.EMPTY_SUBCATEGORY, 0),
                ('Income', 'Dividends', 0),
                ('Income', 'Interest', 0),
                ('Income', 'Salary / Wages', 0),
                ('Income', 'Unemployment', 0),
                ('Savings', self.EMPTY_SUBCATEGORY, 0),
                ('Savings', 'College fund', 0),
                ('Savings', 'Investment', 0),
                ('Savings', 'Retirement', 0),
                ('Shopping', self.EMPTY_SUBCATEGORY, 2),
                ('Shopping', 'Online', 2),
                ('Shopping', 'Amazon', 2),
                ('Transfer', self.EMPTY_SUBCATEGORY, 0),
                ('Medical', self.EMPTY_SUBCATEGORY, 2),
                ('Medical', 'Medicine', 2),
                ('Morgage', self.EMPTY_SUBCATEGORY, 2),
                ('Entertainment', 'Hobbies', 2),
                ('Entertainment', 'Music', 2),
                ('Entertainment', 'Concert', 2),
                ('Tax Preparation', self.EMPTY_SUBCATEGORY, 2),
                ('Work Expense', self.EMPTY_SUBCATEGORY, 2),
                ('Work Expense', 'License', 2),
                ('Auto', 'Rental', 1)
            ]
            logging.info(f'Loading default categories')
            result = result.executemany(
                f'INSERT OR REPLACE INTO {self.CATEGORY_TABLE_NAME} (name, subcategory, expense_type) VALUES (?, ?, ?)',
                default_categories
            )
            logging.debug(f'Committing default categories')
            self.connection.commit()
            logging.debug(f'Default categories load result: {result}')
    def execute(self, sql, params=None):
        cursor = self.connection.cursor()
        logging.debug(f'EXECUTE: {sql}')
        if params:
            return cursor.execute(sql, params)
        else:
            return cursor.execute(sql)
    def _open_database(self):
        """Open encrypted database using SQLCipher"""
        logging.debug(f'Opening encrypted database: {self.db_path}')
        
        if self.connection is None:
            # Use SQLCipher instead of SQLite
            self.connection = sqlcipher3.connect(str(self.db_path))
            
            # Set encryption key if provided
            if self.encryption_key:
                logging.debug("Setting encryption key for database")
                self.connection.execute(f"PRAGMA key='{self.encryption_key}'")
            else:
                # If no key provided, set up encryption interactively
                from budgy.core.security import SecurityManager
                security = SecurityManager()
                key, salt = security.setup_encryption(self.db_path)
                self.connection.execute(f"PRAGMA key='{key}'")
                self.encryption_key = key
                logging.info("Database encryption setup complete")
            
            # Verify encryption is working by testing a simple query
            try:
                self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                logging.debug("Database encryption verification successful")
            except Exception as e:
                raise RuntimeError(f"Database encryption failed - wrong password or corrupted database: {e}")
        
        self._create_txn_table_if_missing()
        self._create_category_table_if_missing()
        self._create_rules_table_if_missing()
        self.migrate_to_auto_fitid()
    def get_record_by_fitid(self, fitid):
        """Get record by our internal auto-generated fitid"""
        sql = f'SELECT * from {self.TXN_TABLE_NAME} WHERE fitid = ?;'
        result = self.execute(sql, (fitid,))
        rows = result.fetchall()
        return rows[0] if len(rows) == 1 else None
    def record_from_row(self, row):
        checknum = "" if row[8] is None else row[8]
        return {
            'fitid': row[0],  # Auto-generated unique ID
            'account': row[1],
            'type': row[2],
            'posted': row[3],
            'amount': row[4],
            'name': row[5],
            'memo': row[6],
            'checknum': checknum
        }
    def insert_record(self, record):
        checknum = "" if record.get('checknum') is None else record['checknum']
        sql = f'INSERT INTO {self.TXN_TABLE_NAME} (account, type, posted, amount, name, memo, checknum) VALUES (?, ?, ?, ?, ?, ?, ?);'
        result = self.execute(sql, (
            record["account"],
            record["type"],
            record["posted"],
            record["amount"],
            record["name"],
            record["memo"],
            checknum
        ))
        self.connection.commit()
    def find_duplicate_by_content(self, record):
        """Find potential duplicate based on all content fields (ignoring fitid and checknum)"""
        sql = f'''SELECT * FROM {self.TXN_TABLE_NAME}
                  WHERE account = ? AND posted = ? AND amount = ? AND name = ? AND memo = ? AND type = ?'''
        result = self.execute(sql, (
            record['account'],
            record['posted'],
            record['amount'],
            record['name'],
            record['memo'],
            record['type']
        ))
        rows = result.fetchall()
        return rows[0] if len(rows) > 0 else None
    def merge_record(self, record):
        # Check for duplicate content (ignoring bank fitid and checknum)
        duplicate_record = self.find_duplicate_by_content(record)
        if duplicate_record is not None:
            old_record = self.record_from_row(duplicate_record)
            logging.warning('Duplicate found:')
            logging.debug(f'   New: checknum={record.get("checknum", "None")}')
            logging.debug(f'   Old: fitid={old_record["fitid"]}, checknum={old_record.get("checknum", "None")}')
            logging.info(f'   Transaction: {record["posted"]} | {record["amount"]} | {record["name"][:50]}...')
            # Since all major fields match (account, posted, amount, name, memo, type),
            # this is definitely a duplicate
            logging.info('   SKIPPING: All content fields match, treating as duplicate')
            logging.warning(f'Skipped duplicate: existing_fitid={old_record["fitid"]}')
            return
        # Insert new record (fitid will be auto-generated)
        logging.debug(f'New record, inserting: {record["account"]}|{record["posted"]}')
        self.insert_record(record)
    def get_date_range(self):
        sql = f'SELECT MIN(posted) AS start, MAX(posted) AS end FROM transactions'
        result = self.execute(sql)
        if result is not None:
            logging.debug(f'date range result: "{result}"')
            for row in result:
                logging.debug(f'date range row: "{row}"')
                if row[0] is None or row[1] is None:
                    return (None, None)
                start = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S%z')
                end  = datetime.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S%z')
                return (start, end)
        return (None, None)
    def count_records(self):
        sql = f'SELECT COUNT(*) FROM {self.TXN_TABLE_NAME}'
        result = self.execute(sql)
        count = 0
        if result is not None:
            logging.debug(result)
            for row in result:
                return(row[0])
        return 0

    def has_records(self):
        """Check if database has any transaction records"""
        return self.count_records() > 0

    def get_most_recent_month_with_data(self):
        """Get the most recent year/month combination that has transaction data"""
        sql = '''SELECT STRFTIME("%Y", posted) AS year, STRFTIME("%m", posted) AS month
                 FROM transactions
                 ORDER BY posted DESC
                 LIMIT 1'''
        result = self.execute(sql)
        if result:
            row = result.fetchone()
            if row and row[0] and row[1]:
                logging.debug(f'Most recent month: {row[0]}-{row[1]}')
                return (row[0], row[1])  # Returns (year, month) tuple
        logging.debug('No records found for most recent month')
        return None

    def get_report(self):
        sql_old = ('SELECT STRFTIME("%Y", posted) AS year, STRFTIME("%m", posted) AS month, SUM(amount) AS expences '
                   'FROM transactions '
                   'WHERE amount < 0 AND NOT exclude '
                   'GROUP BY year, month ORDER BY year, month DESC;')
        sql = ('SELECT STRFTIME("%Y", posted) AS year, STRFTIME("%m", posted) AS month, SUM(ABS(amount)) AS expences '
               'FROM transactions AS txn '
               'WHERE amount < 0 '
               'GROUP BY year, month ORDER BY year, month DESC;')
        logging.debug(f'Report SQL: {sql}')
        result = self.execute(sql)
        data = {}
        if result is not None:
            for row in result:
                year = row[0]
                expense_month = int(row[1]) - 1
                expense = row[2]
                if year not in data:
                    data[year] = {
                        'months': [None, None, None, None, None, None, None, None, None, None, None, None],
                        'average': None
                    }
                data[year]['months'][expense_month] = expense
            sql = ('SELECT STRFTIME("%Y", posted) AS year, STRFTIME("%m", posted) AS month, SUM(ABS(amount)) AS expences '
                   'FROM transactions AS txn, categories AS cat '
                   'WHERE amount < 0 AND txn.category = cat.id AND NOT cat.expense_type '
                   'GROUP BY year, month ORDER BY year, month DESC;')
            result = self.execute(sql)
            if result is not None:
                for row in result:
                    year = row[0]
                    expense_month = int(row[1]) - 1
                    amount = row[2]
                    data[year]['months'][expense_month] -= amount
            for year in data:
                sum = 0
                n = 0
                data[year]['minimum'] = None
                data[year]['maximum'] = None
                max_expense = None
                for monthly_expense in data[year]['months']:
                    # NOTE: expenses are negative so the max expense is less-than the others
                    if monthly_expense is not None:
                        if data[year]['minimum'] is None:
                            data[year]['minimum'] = monthly_expense
                        else:
                            if monthly_expense < data[year]['minimum']:
                                data[year]['minimum'] = monthly_expense
                        if data[year]['maximum'] is None:
                            data[year]['maximum'] = monthly_expense
                        else:
                            if monthly_expense > data[year]['maximum']:
                                data[year]['maximum'] = monthly_expense
                        sum += float(monthly_expense)
                        n += 1
                data[year]['average'] = sum / n
        return data
    def all_records(self, year=None, month=None) -> List[Dict]:
        where_clause = ''
        params = []
        if year is not None or month is not None:
            where_clause = ' WHERE '
            and_clause = ''
            if year is not None:
                where_clause += 'STRFTIME("%Y", posted) = ?'
                params.append(year)
                and_clause = ' AND '
            if month is not None:
                where_clause += and_clause + 'STRFTIME("%m", posted) = ?'
                params.append(month)
        sql = (f'SELECT fitid, account, type, posted, amount, name, memo, checknum, category '
               f'FROM {self.TXN_TABLE_NAME} '
               f'{where_clause}'
               f'ORDER BY posted')
        logging.debug(f'All records SQL: {sql}')
        result = self.execute(sql, tuple(params) if params else None)
        records = []
        if result is not None:
            for record in result:
                records.append({
                    'fitid': record[0],
                    'account': record[1],
                    'type': record[2],
                    'posted': record[3],
                    'amount': record[4],
                    'name': record[5],
                    'memo': record[6],
                    'checknum': record[7],
                    'category': record[8] if record[8] != '' else self.DEFAULT_CATEGORY
                })
        return records
    def delete_all_records(self):
        sql = f'DELETE FROM {self.TXN_TABLE_NAME}'
        result = self.execute(sql)
        self.connection.commit()
        logging.info('All records deleted from database')
    def merge_records(self, newrecords):
        result = {
            'merged': 0
        }
        logging.info(f'Merging {len(newrecords)} records')
        for record in newrecords:
            self.merge_record(record)
    def get_catetory_dict(self):
        sql = f'SELECT name, subcategory, expense_type, id FROM {self.CATEGORY_TABLE_NAME} ORDER BY name'
        result = self.execute(sql)
        category_dict = {}
        for row in result:
            if not row[0] in category_dict:
                category_dict[row[0]] = {}
            category_dict[row[0]][row[1]] = {'expense_type': row[2], 'id': row[3]}
        return category_dict
    def get_category_list(self):
        sql = f'SELECT DISTINCT name FROM {self.CATEGORY_TABLE_NAME} ORDER BY name'
        result = self.execute(sql)
        category_list = []
        for record in result:
            if record[0] == self.DEFAULT_CATEGORY:
                category_list.insert(0, {'name': record[0]})
            else:
                category_list.append({
                    'name': record[0]
                })
        return category_list
    def get_category_for_fitid(self, fitid):
        if fitid is None:
            return [self.DEFAULT_CATEGORY, '', 0]
        sql = f'SELECT c.name, c.subcategory, c.expense_type FROM {self.TXN_TABLE_NAME} AS t, {self.CATEGORY_TABLE_NAME} AS c WHERE t.fitid = ? AND t.category = c.id'
        result = self.execute(sql, (fitid,))
        if not result:
            return [self.DEFAULT_CATEGORY, '', 0]
        rows = result.fetchall()
        if len(rows) == 0:
            return [self.DEFAULT_CATEGORY, '', 0]
        return list(rows[0])
    def get_category_id(self, category, subcategory):
        sql = f'SELECT id FROM {self.CATEGORY_TABLE_NAME} WHERE name = ? AND subcategory = ?'
        result = self.execute(sql, (category, subcategory))
        if not result:
            raise Exception(f'Category not in database: "{category}" / "{subcategory}"')
        for row in result:
            return row[0]
    def set_txn_category(self, fitid, category, subcategory):
        """Set category for transaction using our internal fitid"""
        category_id = self.get_category_id(category, subcategory)
        sql = f'UPDATE {self.TXN_TABLE_NAME} SET category = ? WHERE fitid = ?'
        result = self.execute(sql, (category_id, fitid))
        rows_affected = result.rowcount
        if rows_affected == 0:
            raise Exception(f'No transaction found for fitid={fitid}')
        elif rows_affected > 1:
            raise Exception(f'Multiple transactions updated for fitid={fitid}')
        self.connection.commit()
    def bulk_categorize(self, txn_pattern, category, subcategory=EMPTY_SUBCATEGORY, include_categorized=False):
        category_id = self.get_category_id(category, subcategory)
        if not include_categorized:
            default_category_id = self.get_category_id(self.DEFAULT_CATEGORY, self.EMPTY_SUBCATEGORY)
            sql = f'UPDATE {self.TXN_TABLE_NAME} SET category = ? WHERE name LIKE ? AND category = ?'
            result = self.execute(sql, (category_id, txn_pattern, default_category_id))
        else:
            sql = f'UPDATE {self.TXN_TABLE_NAME} SET category = ? WHERE name LIKE ?'
            result = self.execute(sql, (category_id, txn_pattern))
        if not result:
            raise Exception(f'Bulk Categorize Failed for {txn_pattern} to "{category}" "{subcategory}"')
        self.connection.commit()
    def migrate_to_auto_fitid(self):
        """Migrate existing database to use auto-generated fitids"""
        # Check if we need to migrate by looking at the table structure
        sql = f"PRAGMA table_info({self.TXN_TABLE_NAME})"
        result = self.execute(sql)
        columns = result.fetchall()
        # Check if fitid is already INTEGER PRIMARY KEY AUTOINCREMENT
        fitid_column = None
        for col in columns:
            if col[1] == 'fitid':  # col[1] is column name
                fitid_column = col
                break
        # If fitid exists but is not INTEGER PRIMARY KEY AUTOINCREMENT, we need to migrate
        if fitid_column and (fitid_column[2].upper() != 'INTEGER' or not fitid_column[5]):  # col[5] is pk flag
            logging.info("Migrating database to use auto-generated fitids...")
            # Create new table with auto-generated fitids
            new_table_name = f"{self.TXN_TABLE_NAME}_new"
            sql = f'''CREATE TABLE {new_table_name} (
                fitid INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT,
                type TEXT,
                posted TEXT,
                amount FLOAT,
                name TEXT,
                memo TEXT,
                category INT DEFAULT 1,
                checknum TEXT
            );'''
            self.execute(sql)
            # Copy data from old table (fitid will be auto-generated)
            sql = f'''INSERT INTO {new_table_name} (account, type, posted, amount, name, memo, category, checknum)
                     SELECT account, type, posted, amount, name, memo, category, checknum
                     FROM {self.TXN_TABLE_NAME};'''
            self.execute(sql)
            # Drop old table
            self.execute(f'DROP TABLE {self.TXN_TABLE_NAME}')
            # Rename new table
            self.execute(f'ALTER TABLE {new_table_name} RENAME TO {self.TXN_TABLE_NAME}')
            # Create index for duplicate detection
            sql = f'CREATE INDEX content_lookup ON {self.TXN_TABLE_NAME} (account, posted, amount, name, memo, type);'
            self.execute(sql)
            self.connection.commit()
            logging.info("Migration to auto-generated fitids completed successfully")
        elif fitid_column and fitid_column[2].upper() == 'INTEGER' and fitid_column[5]:
            logging.info("Database already uses auto-generated fitids")
        else:
            logging.info("No migration needed - database appears to be new")
    def migrate_unique_constraint(self):
        """Migrate existing databases to use new unique constraint"""
        old_index_name = 'acct_fitid'
        new_index_name = 'acct_fitid_posted'
        # Check if old index exists and new index doesn't
        if self.index_exists(old_index_name) and not self.index_exists(new_index_name):
            logging.info(f"Migrating database: updating unique constraint to include posted date")
            # Check for existing duplicate records that would violate new constraint
            sql = f'''
                SELECT fitid, account, COUNT(*) as count
                FROM {self.TXN_TABLE_NAME}
                GROUP BY fitid, account
                HAVING count > 1
            '''
            result = self.execute(sql)
            duplicates = result.fetchall()
            if len(duplicates) > 0:
                logging.warning(f"Found {len(duplicates)} fitid/account combinations with multiple records")
                for dup in duplicates:
                    logging.warning(f"  fitid={dup[0]}, account={dup[1]}, count={dup[2]}")
                logging.info("These will be allowed under the new constraint (different posted dates)")
            # Drop old index
            logging.info(f"Dropping old index: {old_index_name}")
            self.execute(f'DROP INDEX IF EXISTS {old_index_name}')
            # Create new index
            logging.info(f"Creating new index: {new_index_name}")
            sql = f'CREATE UNIQUE INDEX {new_index_name} ON {self.TXN_TABLE_NAME} (fitid, account, posted);'
            self.execute(sql)
            self.connection.commit()
            logging.info("Migration completed successfully")
        elif self.index_exists(new_index_name):
            logging.info("Database already migrated - new unique constraint exists")
        else:
            logging.info("No migration needed - database appears to be new")
    def migrate_fitid_to_text(self):
        """Migrate fitid column from INT to TEXT to handle string fitids from banks"""
        # Check if fitid column is currently INT type
        sql = f"PRAGMA table_info({self.TXN_TABLE_NAME})"
        result = self.execute(sql)
        columns = result.fetchall()
        fitid_column = None
        for col in columns:
            if col[1] == 'fitid':  # col[1] is column name
                fitid_column = col
                break
        if fitid_column and fitid_column[2].upper() == 'INT':  # col[2] is column type
            logging.info("Migrating fitid column from INT to TEXT")
            # Create new table with TEXT fitid
            new_table_name = f"{self.TXN_TABLE_NAME}_new"
            sql = f'''CREATE TABLE {new_table_name} (
                fitid TEXT,
                account TEXT,
                type TEXT,
                posted TEXT,
                amount FLOAT,
                name TEXT,
                memo TEXT,
                category INT DEFAULT 1,
                checknum TEXT
            );'''
            self.execute(sql)
            # Copy data from old table to new table
            sql = f'''INSERT INTO {new_table_name}
                     SELECT CAST(fitid AS TEXT), account, type, posted, amount, name, memo, category, checknum
                     FROM {self.TXN_TABLE_NAME};'''
            self.execute(sql)
            # Drop old table
            self.execute(f'DROP TABLE {self.TXN_TABLE_NAME}')
            # Rename new table
            self.execute(f'ALTER TABLE {new_table_name} RENAME TO {self.TXN_TABLE_NAME}')
            # Recreate the unique index
            sql = f'CREATE UNIQUE INDEX acct_fitid_posted ON {self.TXN_TABLE_NAME} (fitid, account, posted);'
            self.execute(sql)
            self.connection.commit()
            logging.info("fitid migration completed successfully")
        elif fitid_column and fitid_column[2].upper() == 'TEXT':
            logging.info("fitid column already migrated to TEXT")
        else:
            logging.error("fitid column not found - database may be corrupted")
