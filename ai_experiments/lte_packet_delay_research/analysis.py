#!/usr/bin/env python3
"""
LTE Packet Delay Counter Research Script
Searches for technical documentation on L.Traffic.DL.PktDelay.Time.QCI and related counters
"""

import json
import os
from pathlib import Path

# Tavily Search API integration
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("WARNING: Tavily client not available, using alternative search methods")

def perform_tavily_search(query, max_results=10):
    """Perform search using Tavily API"""
    if not TAVILY_AVAILABLE:
        return []
    
    try:
        api_key = os.environ.get('TAVILY_API_KEY', 'tvly-demo')  # Use demo key or env var
        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=max_results, search_depth="advanced")
        return response.get('results', [])
    except Exception as e:
        print(f"Tavily search error for '{query}': {e}")
        return []

def save_results(filename, data):
    """Save research results to file"""
    output_dir = Path('/home/alex/code/lng_chain/ai_experiments/lte_packet_delay_research/results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved: {filepath}")
    return str(filepath)

# Main research queries
queries = [
    # Technical counter descriptions
    "L.Traffic.DL.PktDelay.Time.QCI LTE counter formula calculation PDCP RLC",
    "E-RAB.PktDelay.Avg 3GPP measurement definition",
    "LTE packet delay measurement Layer 2 PDCP delay formula",
    
    # Vendor documentation
    "Huawei L.Traffic.DL.PktDelay.Time.QCI counter description manual",
    "Ericsson LTE packet delay counter KPI definition",
    "Nokia LTE eNB packet delay measurement counter",
    "ZTE LTE performance counters packet delay QCI",
    
    # 3GPP standards
    "3GPP TS 36.314 Layer 2 measurements packet delay",
    "3GPP TS 28.552 packet delay measurement definition",
    "3GPP TS 23.203 QCI characteristics latency",
    
    # Research papers and whitepapers
    "LTE packet delay measurement research paper QoE impact",
    "LTE network packet delay optimization techniques whitepaper",
    "typical LTE packet delay values production networks KPI benchmarks"
]

print("=" * 80)
print("LTE PACKET DELAY COUNTER RESEARCH")
print("=" * 80)
print(f"\nTavily API available: {TAVILY_AVAILABLE}")
print(f"Number of queries: {len(queries)}\n")

all_results = {}

for i, query in enumerate(queries, 1):
    print(f"[{i}/{len(queries)}] Searching: {query[:60]}...")
    results = perform_tavily_search(query, max_results=10)
    
    if results:
        all_results[query] = []
        for r in results:
            entry = {
                'title': r.get('title', ''),
                'url': r.get('url', ''),
                'content': r.get('content', '')[:2000],  # Limit content length
                'score': r.get('score', 0)
            }
            all_results[query].append(entry)
        print(f"  Found {len(results)} results")
    else:
        print(f"  No results found")

# Save comprehensive results
results_path = save_results('search_results.json', all_results)

# Create summary report
summary = {
    'research_date': '2024',
    'total_queries': len(queries),
    'queries_with_results': sum(1 for v in all_results.values() if v),
    'results_file': results_path,
    'key_findings': []
}

# Extract key findings from results
for query, results in all_results.items():
    if results:
        summary['key_findings'].append({
            'query': query,
            'top_result_title': results[0].get('title', ''),
            'top_result_url': results[0].get('url', ''),
            'result_count': len(results)
        })

summary_path = save_results('research_summary.json', summary)

print("\n" + "=" * 80)
print("RESEARCH COMPLETE")
print("=" * 80)
print(f"Full results: {results_path}")
print(f"Summary: {summary_path}")

# Print key findings to stdout
print("\nKEY FINDINGS:")
for finding in summary['key_findings']:
    print(f"\nQuery: {finding['query'][:70]}")
    print(f"  Top result: {finding['top_result_title']}")
    print(f"  URL: {finding['top_result_url']}")
