import logging
from pathlib import Path

import ofxtools
from ofxtools.Parser import OFXTree

ofxtools_logger = logging.getLogger('ofxtools')
ofxtools_logger.setLevel(logging.ERROR)
ofxparser_logger = logging.getLogger('ofxtools.Parser')
ofxparser_logger.setLevel(logging.ERROR)


def load_ofx_file(ofxfile: Path):
    parser = OFXTree()
    parser.parse(ofxfile)
    ofx = parser.convert()
    records = []
    logging.info(f'{len(ofx.statements)} statements')
    for statement in ofx.statements:
        is_checking = isinstance(statement, ofxtools.models.bank.stmt.STMTRS)
        account = statement.bankacctfrom.acctid if is_checking else statement.ccacctfrom.acctid
        for txn in statement.transactions:
            checknum = txn.checknum if is_checking else ''
            if checknum is None:
                checknum = ""
            record = {
                'account': account,
                'type': txn.trntype,
                'posted': str(txn.dtposted),
                'amount': float(txn.trnamt),
                'name': txn.name,
                'memo': txn.memo,
                'checknum': checknum
            }
            logging.debug(f'{record["posted"]}|{record["account"]}|{record["name"]}|{record["amount"]}')

            records.append(record)
        logging.debug('')
    return records