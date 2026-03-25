#!/usr/bin/env python3
"""
AMCIS 9.0 Node Runner

Usage:
    python run_node.py --node-id 0 --port 10000 --nodes 0,1,2,3
    python run_node.py --node-id 1 --port 10001 --nodes 0,1,2,3 --bootstrap localhost:10000
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from amcis9 import AMCISNode, NodeConfig


def setup_logging(node_id: int, verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format=f'[Node {node_id}] %(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'amcis9_node_{node_id}.log')
        ]
    )


async def main():
    parser = argparse.ArgumentParser(description='AMCIS 9.0 Node')
    parser.add_argument('--node-id', type=int, required=True, help='Node ID')
    parser.add_argument('--port', type=int, default=0, help='Port to listen on')
    parser.add_argument('--nodes', type=str, required=True, help='Comma-separated list of all node IDs')
    parser.add_argument('--bootstrap', type=str, help='Comma-separated list of bootstrap peers (host:port)')
    parser.add_argument('--data-dir', type=str, default='./amcis_data', help='Data directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Parse node list
    all_nodes = [int(n.strip()) for n in args.nodes.split(',')]
    
    if args.node_id not in all_nodes:
        print(f"Error: Node ID {args.node_id} not in node list {all_nodes}")
        sys.exit(1)
    
    # Parse bootstrap peers
    bootstrap = []
    if args.bootstrap:
        for peer in args.bootstrap.split(','):
            host, port = peer.strip().split(':')
            bootstrap.append((host, int(port)))
    
    # Setup logging
    setup_logging(args.node_id, args.verbose)
    
    # Create config
    config = NodeConfig(
        node_id=args.node_id,
        all_nodes=all_nodes,
        port=args.port,
        bootstrap_peers=bootstrap if bootstrap else None,
        data_dir=f"{args.data_dir}/node_{args.node_id}",
        enable_audit_logging=True,
        enable_quantum_channel=True
    )
    
    # Create and start node
    node = AMCISNode(config)
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print(f"\n[Node {args.node_id}] Shutting down...")
        asyncio.create_task(node.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                    AMCIS 9.0 Node                             ║
║          Advanced Modular Cybersecurity Infrastructure        ║
╠═══════════════════════════════════════════════════════════════╣
║  Node ID: {args.node_id:<4}                                          ║
║  Peers:   {len(all_nodes) - 1:<4}                                          ║
║  Port:    {args.port if args.port else 'Auto':<4}                                          ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    success = await node.start()
    
    if not success:
        print(f"[Node {args.node_id}] Failed to start!")
        sys.exit(1)
    
    print(f"[Node {args.node_id}] Started successfully. Press Ctrl+C to stop.")
    
    # Print status periodically
    try:
        while node.running:
            await asyncio.sleep(30)
            status = node.get_status()
            print(f"\n[Node {args.node_id}] Status: {json.dumps(status, indent=2, default=str)}")
    except asyncio.CancelledError:
        pass
    
    await node.stop()
    print(f"[Node {args.node_id}] Stopped.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
