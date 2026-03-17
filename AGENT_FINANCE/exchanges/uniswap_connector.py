"""
Uniswap V3 Connector - Web3 DeFi Integration
Decentralized exchange trading via smart contracts
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import json
import time

logger = logging.getLogger(__name__)


class UniswapConnector:
    """
    Uniswap V3 DeFi Connector
    Supports: Swaps, Liquidity provision, Position management
    """
    
    # Contract addresses (Ethereum mainnet)
    FACTORY_ADDRESS = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
    ROUTER_ADDRESS = "0xE592427A0AEce92De3Edee1F18E0157C05861564"  # SwapRouter
    QUOTER_ADDRESS = "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6"
    NPM_ADDRESS = "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"  # NonfungiblePositionManager
    
    # Common token addresses
    TOKENS = {
        'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        'USDC': '0xA0b86a33E6441e6a1c32c0eeD2E9b8f6E3F5B8A0',
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
        'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
    }
    
    # Fee tiers
    FEE_TIERS = {
        'LOW': 500,      # 0.05%
        'MEDIUM': 3000,  # 0.3%
        'HIGH': 10000    # 1%
    }
    
    def __init__(self, rpc_url: str, private_key: str, 
                 wallet_address: str, chain_id: int = 1):
        self.rpc_url = rpc_url
        self.private_key = private_key
        self.wallet_address = wallet_address
        self.chain_id = chain_id
        
        # Web3 will be initialized in connect()
        self.w3 = None
        self.router = None
        self.quoter = None
        self.npm = None
        
        # Token contracts cache
        self._token_contracts = {}
        self._decimals_cache = {}
        
        logger.info(f"Uniswap connector initialized for chain {chain_id}")
        
    async def connect(self):
        """Initialize Web3 connection"""
        try:
            from web3 import Web3
            
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            
            if not self.w3.is_connected():
                raise Exception("Failed to connect to RPC")
                
            # Load contract ABIs (simplified)
            self.router = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.ROUTER_ADDRESS),
                abi=self._get_router_abi()
            )
            
            self.quoter = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.QUOTER_ADDRESS),
                abi=self._get_quoter_abi()
            )
            
            logger.info(f"Connected to chain {self.chain_id}, block: {self.w3.eth.block_number}")
            
        except Exception as e:
            logger.error(f"Web3 connection failed: {e}")
            raise
            
    async def close(self):
        """Close connection"""
        self.w3 = None
        
    # ========== Quotes & Pricing ==========
    
    async def get_quote(self, token_in: str, token_out: str, 
                       amount_in: Decimal, fee: int = 3000) -> Decimal:
        """Get quote for exact input swap"""
        try:
            token_in_addr = self._get_token_address(token_in)
            token_out_addr = self._get_token_address(token_out)
            
            amount_in_wei = self._to_wei(amount_in, token_in)
            
            # Call quoter contract
            amount_out = self.quoter.functions.quoteExactInputSingle(
                self.w3.to_checksum_address(token_in_addr),
                self.w3.to_checksum_address(token_out_addr),
                fee,
                amount_in_wei,
                0  # sqrtPriceLimitX96
            ).call()
            
            return self._from_wei(amount_out, token_out)
            
        except Exception as e:
            logger.error(f"Quote failed: {e}")
            return Decimal('0')
            
    async def get_quote_exact_out(self, token_in: str, token_out: str,
                                  amount_out: Decimal, fee: int = 3000) -> Decimal:
        """Get quote for exact output swap"""
        try:
            token_in_addr = self._get_token_address(token_in)
            token_out_addr = self._get_token_address(token_out)
            
            amount_out_wei = self._to_wei(amount_out, token_out)
            
            amount_in = self.quoter.functions.quoteExactOutputSingle(
                self.w3.to_checksum_address(token_in_addr),
                self.w3.to_checksum_address(token_out_addr),
                fee,
                amount_out_wei,
                0
            ).call()
            
            return self._from_wei(amount_in, token_in)
            
        except Exception as e:
            logger.error(f"Quote failed: {e}")
            return Decimal('0')
            
    # ========== Swaps ==========
    
    async def swap_exact_in(self, token_in: str, token_out: str,
                           amount_in: Decimal, min_amount_out: Decimal,
                           fee: int = 3000) -> Dict:
        """Execute exact input swap"""
        try:
            token_in_addr = self._get_token_address(token_in)
            token_out_addr = self._get_token_address(token_out)
            
            amount_in_wei = self._to_wei(amount_in, token_in)
            min_out_wei = self._to_wei(min_amount_out, token_out)
            
            # Build transaction
            deadline = int(time.time()) + 300  # 5 min deadline
            
            params = {
                'tokenIn': self.w3.to_checksum_address(token_in_addr),
                'tokenOut': self.w3.to_checksum_address(token_out_addr),
                'fee': fee,
                'recipient': self.w3.to_checksum_address(self.wallet_address),
                'deadline': deadline,
                'amountIn': amount_in_wei,
                'amountOutMinimum': min_out_wei,
                'sqrtPriceLimitX96': 0
            }
            
            # Build and send transaction
            tx = self.router.functions.exactInputSingle(params).build_transaction({
                'from': self.wallet_address,
                'gas': 200000,
                'gasPrice': self.w3.to_wei('50', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                'success': receipt['status'] == 1,
                'tx_hash': tx_hash.hex(),
                'gas_used': receipt['gasUsed'],
                'block_number': receipt['blockNumber']
            }
            
        except Exception as e:
            logger.error(f"Swap failed: {e}")
            return {'success': False, 'error': str(e)}
            
    async def swap_exact_out(self, token_in: str, token_out: str,
                            max_amount_in: Decimal, amount_out: Decimal,
                            fee: int = 3000) -> Dict:
        """Execute exact output swap"""
        try:
            token_in_addr = self._get_token_address(token_in)
            token_out_addr = self._get_token_address(token_out)
            
            max_in_wei = self._to_wei(max_amount_in, token_in)
            amount_out_wei = self._to_wei(amount_out, token_out)
            
            deadline = int(time.time()) + 300
            
            params = {
                'tokenIn': self.w3.to_checksum_address(token_in_addr),
                'tokenOut': self.w3.to_checksum_address(token_out_addr),
                'fee': fee,
                'recipient': self.w3.to_checksum_address(self.wallet_address),
                'deadline': deadline,
                'amountOut': amount_out_wei,
                'amountInMaximum': max_in_wei,
                'sqrtPriceLimitX96': 0
            }
            
            tx = self.router.functions.exactOutputSingle(params).build_transaction({
                'from': self.wallet_address,
                'gas': 200000,
                'gasPrice': self.w3.to_wei('50', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                'success': receipt['status'] == 1,
                'tx_hash': tx_hash.hex(),
                'gas_used': receipt['gasUsed'],
                'block_number': receipt['blockNumber']
            }
            
        except Exception as e:
            logger.error(f"Swap failed: {e}")
            return {'success': False, 'error': str(e)}
            
    # ========== Liquidity (LP) ==========
    
    async def add_liquidity(self, token0: str, token1: str, 
                           amount0: Decimal, amount1: Decimal,
                           fee: int = 3000, tick_lower: int = None,
                           tick_upper: int = None) -> Dict:
        """Add liquidity to a pool"""
        # This requires NonfungiblePositionManager
        # Implementation would mint a new LP NFT position
        pass
        
    async def remove_liquidity(self, token_id: int) -> Dict:
        """Remove liquidity and collect fees"""
        pass
        
    async def collect_fees(self, token_id: int) -> Dict:
        """Collect accumulated fees from LP position"""
        pass
        
    # ========== Account ==========
    
    async def get_balance(self, token: str) -> Decimal:
        """Get token balance"""
        try:
            if token.upper() == 'ETH':
                balance_wei = self.w3.eth.get_balance(self.wallet_address)
                return self.w3.from_wei(balance_wei, 'ether')
            else:
                token_addr = self._get_token_address(token)
                
                # ERC20 balanceOf
                token_contract = self._get_token_contract(token_addr)
                balance = token_contract.functions.balanceOf(
                    self.w3.to_checksum_address(self.wallet_address)
                ).call()
                
                return self._from_wei(balance, token)
                
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return Decimal('0')
            
    async def approve_token(self, token: str, spender: str, 
                           amount: Decimal) -> Dict:
        """Approve token spending"""
        try:
            token_addr = self._get_token_address(token)
            token_contract = self._get_token_contract(token_addr)
            
            amount_wei = self._to_wei(amount, token)
            
            tx = token_contract.functions.approve(
                self.w3.to_checksum_address(spender),
                amount_wei
            ).build_transaction({
                'from': self.wallet_address,
                'gas': 100000,
                'gasPrice': self.w3.to_wei('50', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address)
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                'success': receipt['status'] == 1,
                'tx_hash': tx_hash.hex()
            }
            
        except Exception as e:
            logger.error(f"Approval failed: {e}")
            return {'success': False, 'error': str(e)}
            
    # ========== Helpers ==========
    
    def _get_token_address(self, symbol: str) -> str:
        """Get token contract address"""
        symbol = symbol.upper()
        if symbol in self.TOKENS:
            return self.TOKENS[symbol]
        # Assume it's already an address
        return symbol
        
    def _get_token_contract(self, address: str):
        """Get or load token contract"""
        if address not in self._token_contracts:
            erc20_abi = self._get_erc20_abi()
            self._token_contracts[address] = self.w3.eth.contract(
                address=self.w3.to_checksum_address(address),
                abi=erc20_abi
            )
        return self._token_contracts[address]
        
    def _get_decimals(self, token: str) -> int:
        """Get token decimals"""
        if token in self._decimals_cache:
            return self._decimals_cache[token]
            
        try:
            if token.upper() == 'ETH':
                decimals = 18
            else:
                token_addr = self._get_token_address(token)
                contract = self._get_token_contract(token_addr)
                decimals = contract.functions.decimals().call()
                
            self._decimals_cache[token] = decimals
            return decimals
            
        except:
            return 18  # Default
            
    def _to_wei(self, amount: Decimal, token: str) -> int:
        """Convert to wei units"""
        decimals = self._get_decimals(token)
        return int(amount * (Decimal(10) ** decimals))
        
    def _from_wei(self, amount: int, token: str) -> Decimal:
        """Convert from wei units"""
        decimals = self._get_decimals(token)
        return Decimal(amount) / (Decimal(10) ** decimals)
        
    def _get_router_abi(self) -> List[Dict]:
        """Router contract ABI (simplified)"""
        return json.loads('[{"inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct IV3SwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]')
        
    def _get_quoter_abi(self) -> List[Dict]:
        """Quoter contract ABI (simplified)"""
        return json.loads('[{"inputs":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"name":"quoteExactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]')
        
    def _get_erc20_abi(self) -> List[Dict]:
        """ERC20 token ABI"""
        return [
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
            {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
        ]
