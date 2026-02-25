
import asyncio
import time
import random
from stem import Signal
from stem.control import Controller

# =========================================================
# GLOBAL TOR MANAGER (Hardened Rate Limiting)
# =========================================================
class TorManager:
    """
    Manages global Tor state to prevent session conflicts and 
    simultaneous IP rotations without freezing workers.
    """
    _lock = asyncio.Lock()
    _last_renewal = 0
    _is_cooldown = False
    
    # OPTIMIZED: Background rotation without blocking worker pool
    _cooldown_duration = 5 

    @classmethod
    async def renew_identity(cls, control_port=9151):
        # We don't want to block the caller awaiting this if it's already rotating
        if cls._is_cooldown:
            return False
            
        async with cls._lock:
            now = time.time()
            # Prevent renewals more frequent than once every 10 seconds (optimized from 30s)
            if now - cls._last_renewal < 10:
                print("⏳ Tor rotation requested too soon. Skipping...")
                return False

            cls._is_cooldown = True
            print("🌀 [GLOBAL LOCK] Requesting Tor IP Rotation...")
            
            # Run the synchronous Tor controller call in a background thread 
            # so we don't block the async event loop at all!
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, renew_tor_identity, control_port)
            
            if success:
                cls._last_renewal = time.time()
                print(f"🚥 Circuit rebuilding... IP Rotation in background...")
            
            # Immediately release. Workers just keep trying and will hit the new IP or backoff
            cls._is_cooldown = False
            return success

    @classmethod
    async def wait_if_cooldown(cls):
        # OPTIMIZED: We no longer force every worker to sleep. 
        # If Tor is rotating, the connection attempt itself might be slightly delayed by the OS
        # or it will just fail and get retried. We just add a tiny jitter to prevent immediate hammering.
        if cls._is_cooldown:
            await asyncio.sleep(random.uniform(0.1, 0.5))

# Signals Tor for a New Identity (Change IP).
# Tor Browser Control Port is usually 9151.
# Tor Service Control Port is usually 9051.
def renew_tor_identity(control_port=9151):
    """
    Signals Tor for a New Identity (Change IP).
    """
    try:
        with Controller.from_port(port=control_port) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            # Short sleep to allow the circuit to be rebuilt (handled by manager now, but good for safety)
            time.sleep(1)
            print("✅ Tor identity renewed successfully.")
            return True
    except Exception as e:
        print(f"❌ Failed to renew Tor identity: {e}")
        return False
