#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
##
# Description:-
#
#       Batch ingestion CLI utility for Multi-Terabyte Enterprise RAG.
#       Scans target directory, detects supported document formats, invokes
#       specialized parser plugins, and commits indexed chunks to the Enterprise Hybrid Index.
#
##
# Development date    Developed by       Comments
# ----------------    ------------       ---------
# 14/11/2024          Saddam Khan        Initial implementation
# 18/12/2024          Saddam Khan        Added multi-format document chunking and GCS ingestion
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import os
import sys
import glob
from parsers.factory import ParserFactory
from indexing.hybrid_index import EnterpriseHybridIndex
from utils.auth import verify_adc

def batch_ingest_directory(dir_path: str, index: EnterpriseHybridIndex):
    """
    Explanation: Iterates through files in a directory, extracts semantic chunks, and indexes them
    :param  dir_path str: Local filesystem path to directory containing documents
    :param  index EnterpriseHybridIndex: Target hybrid index to receive chunk payloads
    :return None: Modifies index in place
    """
    print(f"[*] Scanning directory: {dir_path}")
    files = glob.glob(os.path.join(dir_path, "*.*"))
    if not files:
        print("[!] No files found.")
        return

    total_chunks = 0
    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        _, ext = os.path.splitext(fname.lower())
        if ext not in ParserFactory.supported_extensions():
            continue

        print(f" -> Ingesting '{fname}' ({ext})... ", end="", flush=True)
        try:
            with open(fpath, "rb") as f:
                content = f.read()
            parser = ParserFactory.get_parser(fname)
            chunks = parser.parse_bytes(content, fname)
            index.add_chunks(chunks)
            total_chunks += len(chunks)
            print(f"[✓] {len(chunks)} chunks indexed.")
        except Exception as e:
            print(f"[x] Error: {e}")

    print(f"\n[✓] Ingestion complete. Indexed {total_chunks} total chunks into {index.backend_name} index.")

def main():
    """
    Explanation: CLI entrypoint for triggering directory batch ingestion and displaying stats
    :return None: Executes batch ingestion job
    """
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "sample_data"
    is_valid, proj = verify_adc()
    print("=" * 70)
    print("     Enterprise RAG Batch Ingestion Utility")
    print("=" * 70)
    print(f"[*] ADC Status: {'Active (' + proj + ')' if is_valid else 'Not Configured'}")
    
    index = EnterpriseHybridIndex()
    batch_ingest_directory(target_dir, index)
    stats = index.get_stats()
    print("\n--- Knowledge Base Index Statistics ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
