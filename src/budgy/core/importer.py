import argparse
import logging
from pathlib import Path

from budgy.core.database import BudgyDatabase
from budgy.core.security import SecurityManager
from budgy.core import load_ofx_file

class ImporterApp:
    def __init__(self, db_path, datafiles):
        """
        Initialize the OFX importer.
        
        Args:
            db_path: Path to encrypted database file
            datafiles: List of OFX files to import
        """
        self.db_path = Path(db_path)
        self.datafiles = [Path(f) for f in datafiles]
        
        self._db = BudgyDatabase(self.db_path)
        self._security = SecurityManager()
        # Ensure file encryption is available - fail fast if not
        self._security.get_file_encryption_key()

    def run(self):
        logging.info('Starting OFX import process')
        
        nrecords0 = self._db.count_records()
        if nrecords0 > 0:
            logging.info(f'Database already contains {nrecords0} records')
            
        # Track files for encryption
        files_to_encrypt = []
        
        for datafile in self.datafiles:
            logging.info(f'Importing {datafile}...')
            
            try:
                records = load_ofx_file(datafile)
                self._db.merge_records(records)
                files_to_encrypt.append(datafile)
                
            except Exception as e:
                logging.error(f'Failed to import {datafile}: {e}')
                continue
        
        nrecords1 = self._db.count_records()
        logging.info(f'Database now contains {nrecords1} records')
        new_records = nrecords1 - nrecords0
        if new_records > 0:
            logging.info(f' - Added {new_records} records')
        else:
            logging.info(' - No new records added.')
            
        # Always encrypt OFX files after successful import and delete originals
        if files_to_encrypt:
            logging.info(f'Encrypting {len(files_to_encrypt)} imported OFX files...')
            self._encrypt_ofx_files(files_to_encrypt)
    
    def _encrypt_ofx_files(self, file_paths):
        """Encrypt OFX files and securely delete originals"""
        encrypted_count = 0
        for file_path in file_paths:
            try:
                # Encrypt the file
                encrypted_path = self._security.encrypt_file(file_path)
                
                # Securely delete the original unencrypted file
                if self._security.secure_delete(file_path):
                    encrypted_count += 1
                    logging.info(f'Encrypted and deleted original: {file_path} -> {encrypted_path}')
                else:
                    logging.error(f'Failed to securely delete original: {file_path}')
                    
            except Exception as e:
                logging.error(f'Failed to encrypt {file_path}: {e}')
                continue
                
        if encrypted_count > 0:
            logging.info(f'Successfully encrypted {encrypted_count} OFX files and deleted originals')
        else:
            logging.warning('No OFX files were encrypted')


def main():
    parser = argparse.ArgumentParser(description='Budgy OFX Data Importer')
    parser.add_argument('--db', type=Path, required=True, 
                       help='Path to encrypted database. Will be created if it does not exist')
    parser.add_argument('datafiles', nargs='+', 
                       help='One or more OFX datafiles to import')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        importer = ImporterApp(args.db, args.datafiles)
        importer.run()
    except Exception as e:
        logging.error(f'Import failed: {e}')
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
