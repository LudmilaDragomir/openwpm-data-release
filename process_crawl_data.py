import sys
import sqlite3
import os
from time import time
from util import CRAWL_DB_EXT, get_table_and_column_names, load_alexa_ranks,\
    copy_if_not_exists
from os.path import join, isfile, basename, isdir, dirname, sep
import glob
from normalize_db import add_site_visits_table, add_alexa_rank_to_site_visits,\
    add_missing_columns_to_all_tables, rename_crawl_history_table
from db_schema import SITE_VISITS_TABLE, CRAWL_HISTORY_TABLE
from analyze_crawl import CrawlDBAnalysis

ROOT_OUT_DIR = "/mnt/10tb4/census-release"
if not isdir(ROOT_OUT_DIR):
    ROOT_OUT_DIR = "/tmp/census-release"

DB_SCHEMA_DIR = join(ROOT_OUT_DIR, "db-schemas")
LOG_FILES_DIR = join(ROOT_OUT_DIR, "log-files")
ALEXA_RANKS_DIR = join(ROOT_OUT_DIR, "alexa-ranks")
ANALYSIS_OUT_DIR = join(ROOT_OUT_DIR, "analysis")
OUTDIRS = [DB_SCHEMA_DIR, LOG_FILES_DIR,
           ALEXA_RANKS_DIR, ANALYSIS_OUT_DIR]
OPENWPM_LOG_FILENAME = "openwpm.log"
CRONTAB_LOG_FILENAME = "crontab.log"
ALEXA_TOP1M_CSV_FILENAME = "top-1m.csv"
JAVASCRIPT_SRC_DIRNAME = "content.ldb"
DEFAULT_SQLITE_CACHE_SIZE_GB = 16

ADD_MISSING_COLUMNS = True


class CrawlData(object):

    def __init__(self, crawl_dir):
        self.set_crawl_dir(crawl_dir)
        self.crawl_name = basename(crawl_dir.rstrip(sep))
        self.crawl_db_path = ""
        self.openwpm_log_path = ""
        self.crontab_log_path = ""
        self.alexa_csv_path = ""
        self.init_out_dirs()
        self.set_db_path()
        self.set_crawl_file_paths()
        self.check_js_src_code()
        self.db_conn = sqlite3.connect(self.crawl_db_path)
        self.db_conn.row_factory = sqlite3.Row
        self.optimize_db()

    def init_out_dirs(self):
        for _dir in OUTDIRS:
            if not isdir(_dir):
                os.makedirs(_dir)

    def optimize_db(self, size_in_gb=DEFAULT_SQLITE_CACHE_SIZE_GB):
        """ Runs PRAGMA queries to make sqlite better """
        self.db_conn.execute("PRAGMA cache_size = -%i" % (size_in_gb * 10**6))
        # Store temp tables, indices in memory
        self.db_conn.execute("PRAGMA temp_store = 2")
        # self.db_conn.execute("PRAGMA synchronous = NORMAL;")
        self.db_conn.execute("PRAGMA synchronous = OFF;")
        # self.db_conn.execute("PRAGMA journal_mode = WAL;")
        self.db_conn.execute("PRAGMA journal_mode = OFF;")

    def vacuum_db(self):
        """."""
        print "Will vacuum the DB",
        t0 = time()
        self.db_conn.execute("VACUUM;")
        print "finished in", float(time() - t0) / 60, "mins"

    def set_crawl_dir(self, crawl_dir):
        if isdir(crawl_dir):
            self.crawl_dir = crawl_dir
        else:
            print "Missing crawl dir (archive name mismatch)", crawl_dir
            crawl_dir_pattern = join(dirname(crawl_dir), "*201*")
            self.crawl_dir = glob.glob(crawl_dir_pattern)[0]
        print "Crawl dir", self.crawl_dir

    def check_js_src_code(self):
        js_sources_dir = join(self.crawl_dir, JAVASCRIPT_SRC_DIRNAME)
        self.has_js_src = isdir(js_sources_dir)

    def set_crawl_file_paths(self):
        openwpm_log_path = join(self.crawl_dir, OPENWPM_LOG_FILENAME)
        if isfile(openwpm_log_path):
            self.openwpm_log_path = openwpm_log_path

        crontab_log_path = join(self.crawl_dir, CRONTAB_LOG_FILENAME)
        if isfile(crontab_log_path):
            self.crontab_log_path = crontab_log_path

        alexa_csv_path = join(self.crawl_dir, ALEXA_TOP1M_CSV_FILENAME)
        if isfile(alexa_csv_path):
            self.alexa_csv_path = alexa_csv_path

        print "OpenWPM log", self.openwpm_log_path
        print "Crontab log", self.crontab_log_path
        print "Alexa CSV", self.alexa_csv_path

    def set_db_path(self):
        sqlite_files = glob.glob(join(self.crawl_dir, "*" + CRAWL_DB_EXT))
        assert len(sqlite_files) == 1
        self.crawl_db_path = sqlite_files[0]
        print "Crawl DB path", self.crawl_db_path

    def pre_process(self):
        print "Will pre_process", self.crawl_dir
        self.backup_crawl_files()
        self.dump_db_schema()
        self.normalize_db()
        # self.vacuum_db()

    def normalize_db(self):
        db_schema_str = get_table_and_column_names(self.crawl_db_path)
        # Add site_visits table
        if SITE_VISITS_TABLE not in db_schema_str:
            print "Adding site_visits table"
            add_site_visits_table(self.db_conn)
        if CRAWL_HISTORY_TABLE not in db_schema_str:
            print "Renaming CrawlHistory table to crawl_history"
            rename_crawl_history_table(self.db_conn)
        # Add site ranks to site_visits table
        if "site_rank" not in db_schema_str:
            if self.alexa_csv_path:
                print "Adding Alexa ranks to the site_visits table"
                site_ranks = load_alexa_ranks(self.alexa_csv_path)
                add_alexa_rank_to_site_visits(self.db_conn, site_ranks)
            else:
                print "Missing Alexa ranks CSV, can't add ranks to site_visits"
        if ADD_MISSING_COLUMNS:
            add_missing_columns_to_all_tables(self.db_conn, db_schema_str)
        print "Will commit the changes"
        self.db_conn.commit()

    def dump_db_schema(self):
        self.db_schema_str = get_table_and_column_names(self.crawl_db_path)
        out_str = self.db_schema_str
        out_str += "\nJavascript-source %s\n" % int(self.has_js_src)
        out_fname = self.crawl_name + "-db_schema.txt"
        db_schema_path = join(DB_SCHEMA_DIR, out_fname)
        print "Writing DB schema to %s" % db_schema_path
        with open(db_schema_path, 'w') as out:
            out.write(out_str)

    def backup_crawl_files(self):
        log_prefix = self.crawl_name + "-"
        if self.openwpm_log_path:
            openwpm_log_dst = join(LOG_FILES_DIR,
                                   log_prefix + OPENWPM_LOG_FILENAME)
            copy_if_not_exists(self.openwpm_log_path, openwpm_log_dst)

        if self.crontab_log_path:
            crontab_log_dst = join(LOG_FILES_DIR,
                                   log_prefix + CRONTAB_LOG_FILENAME)
            copy_if_not_exists(self.crontab_log_path, crontab_log_dst)

        if self.alexa_csv_path:
            alexa_csv_dst = join(ALEXA_RANKS_DIR,
                                 log_prefix + ALEXA_TOP1M_CSV_FILENAME)
            copy_if_not_exists(self.alexa_csv_path, alexa_csv_dst)


if __name__ == '__main__':
    t0 = time()
    crawl_data = CrawlData(sys.argv[1])
    crawl_data.pre_process()
    t1 = time()
    print "Preprocess finished in", float(t1 - t0) / 60, "mins"
    analysis = CrawlDBAnalysis(crawl_data.crawl_db_path, ANALYSIS_OUT_DIR,
                               crawl_data.crawl_name)
    analysis.start_analysis()
    print "Analysis finished in", float(time() - t1) / 60, "mins"
