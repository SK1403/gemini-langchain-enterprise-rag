#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
##
# Description:-
#
#       Command-line interface (CLI) for Enterprise Multi-Format Hybrid RAG Assistant.
#       Offers role selection (RBAC), automatic sample corpus loading, multi-turn
#       conversational queries, grounded source citations, and token streaming.
#
##
# Development date    Developed by       Comments
# ----------------    ------------       ---------
# 14/11/2024          Saddam Khan        Initial implementation
# 18/12/2024          Saddam Khan        Added interactive terminal query and batch ingestion CLI
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import sys
import os
from rag_pipeline import EnterpriseRAGPipeline
from ingest import batch_ingest_directory

ROLES = ["all", "engineering", "legal", "finance", "executive"]

def main():
    """
    Explanation: Entrypoint for running interactive Enterprise RAG CLI session
    :return None: Executes CLI loop until exit command or interruption
    """
    print("=" * 75)
    print("       Enterprise Multi-Format Hybrid RAG Assistant (CLI)")
    print("=" * 75)

    pipeline = EnterpriseRAGPipeline()
    print(f"[*] Backend Index: {pipeline.index.backend_name}")
    print(f"[*] Model:         {pipeline.model_name}")
    print(f"[*] Region:        {pipeline.location}")

    # Auto-load sample data if available
    if os.path.exists("sample_data"):
        print("\n[*] Pre-loading enterprise knowledge corpus from 'sample_data/'...")
        batch_ingest_directory("sample_data", pipeline.index)

    active_role = "all"
    print("\nSelect your Enterprise Access Role:")
    for idx, r in enumerate(ROLES, start=1):
        print(f"  [{idx}] {r.upper()}")
    choice = input(f"Choose role [1-{len(ROLES)}] (default 1): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(ROLES):
            active_role = ROLES[idx]
    except ValueError:
        pass

    print(f"\n[✓] Active Role: {active_role.upper()} (RBAC Filtering Enabled)")
    print("Commands: 'role <name>' to switch role, 'clear' to reset, 'exit' to quit.")
    print("-" * 75)

    session_id = "enterprise_cli_session"
    while True:
        try:
            query = input(f"\nEnter Query [{active_role.upper()}]: ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("\nExiting Enterprise Assistant. Goodbye!")
                break
            if query.lower().startswith("role "):
                new_role = query.split()[1].lower()
                if new_role in ROLES:
                    active_role = new_role
                    print(f"[*] Switched role to: {active_role.upper()}")
                else:
                    print(f"[!] Unknown role. Choose from: {ROLES}")
                continue
            if query.lower() in ["clear", "reset"]:
                pipeline.clear_history(session_id)
                print("[*] Session history cleared.")
                continue

            print(f"\nRetrieving & Re-ranking across multi-format index for role '{active_role}'...")
            print("\nEnterprise Assistant: ", end="", flush=True)
            for chunk in pipeline.stream_chat(query, user_role=active_role, session_id=session_id):
                print(chunk, end="", flush=True)
            print()

            # Display citations and score breakdown
            if pipeline.last_retrieved_results:
                print("\n  === Grounded Citations & Audit Trail ===")
                for r in pipeline.last_retrieved_results:
                    c = r.chunk
                    loc = f"Page {c.page}" if c.page else f"Sec: {c.section}"
                    print(f"  • [{c.source} - {loc}] (Format: {c.file_format.upper()})")
                    print(f"    Scores -> Dense: {r.dense_score} | Sparse: {r.sparse_score} | RRF: {r.rrf_score} | Final: {r.final_score}")
                    print(f"    Snippet: \"{c.text.replace(chr(10), ' ')[:100]}...\"")

        except KeyboardInterrupt:
            print("\nSession interrupted. Exiting.")
            break
        except Exception as e:
            print(f"\n[x] Error: {e}")

if __name__ == "__main__":
    main()
