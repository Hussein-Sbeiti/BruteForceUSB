#!/usr/bin/env python3
import os
import sys
import subprocess
import itertools
import time
from multiprocessing import Pool, cpu_count

class USBPasswordBruteForcer:
    def __init__(self, drive_path, wordlist_path=None):
        self.drive_path = drive_path
        self.wordlist_path = wordlist_path
        self.attempts = 0
        self.found_password = None
        
    def test_password(self, password):
        """Test if a password unlocks the USB drive"""
        try:
            # For VeraCrypt encrypted volumes
            if self.is_veracrypt_volume():
                result = subprocess.run(
                    ["veracrypt", "--non-interactive", "--text", 
                     "--password", password, "--mount", self.drive_path, "/tmp/mount"],
                    capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0
                
            # For BitLocker encrypted drives (Windows)
            elif self.is_bitlocker_drive():
                result = subprocess.run(
                    ["manage-bde", "-unlock", self.drive_path, "-password", password],
                    capture_output=True, text=True, timeout=5
                )
                return result.returncode == 0
                
            # For LUKS encrypted drives (Linux)
            elif self.is_luks_volume():
                result = subprocess.run(
                    ["cryptsetup", "open", "--type", "luks", self.drive_path, 
                     "test_mount", "--key-file", "-"],
                    input=password.encode(), capture_output=True, timeout=5
                )
                return result.returncode == 0
                
            # Generic fallback - this is a placeholder and won't work for most encryption
            else:
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def is_veracrypt_volume(self):
        """Check if the drive is a VeraCrypt volume"""
        try:
            result = subprocess.run(
                ["file", self.drive_path],
                capture_output=True, text=True
            )
            return "VeraCrypt" in result.stdout
        except (FileNotFoundError, Exception):
            return False
    
    def is_bitlocker_drive(self):
        """Check if the drive is BitLocker encrypted"""
        try:
            result = subprocess.run(
                ["manage-bde", "-status", self.drive_path],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except (FileNotFoundError, Exception):
            return False
    
    def is_luks_volume(self):
        """Check if the drive is a LUKS encrypted volume"""
        try:
            result = subprocess.run(
                ["cryptsetup", "isLuks", self.drive_path],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except (FileNotFoundError, Exception):
            return False
    
    def dictionary_attack(self):
        """Perform a dictionary attack using a wordlist"""
        if not self.wordlist_path or not os.path.exists(self.wordlist_path):
            print(f"Wordlist not found: {self.wordlist_path}")
            return False
            
        print(f"Starting dictionary attack with {self.wordlist_path}")
        
        with open(self.wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                password = line.strip()
                if not password:
                    continue
                    
                self.attempts += 1
                if self.test_password(password):
                    self.found_password = password
                    print(f"Password found: {password}")
                    return True
                    
                if self.attempts % 100 == 0:
                    print(f"Tested {self.attempts} passwords...")
                    
        return False
    
    def brute_force_attack(self, charset, min_length, max_length):
        """Perform a brute force attack with character set and length range"""
        print(f"Starting brute force attack with charset: {charset}")
        print(f"Testing passwords from length {min_length} to {max_length}")
        
        for length in range(min_length, max_length + 1):
            print(f"Testing passwords of length {length}...")
            
            for attempt in itertools.product(charset, repeat=length):
                password = ''.join(attempt)
                self.attempts += 1
                
                if self.test_password(password):
                    self.found_password = password
                    print(f"Password found: {password}")
                    return True
                    
                if self.attempts % 1000 == 0:
                    print(f"Tested {self.attempts} passwords...")
                    
        return False
    
    def parallel_brute_force(self, charset, min_length, max_length, processes=None):
        """Perform a parallel brute force attack using multiple processes"""
        if not processes:
            processes = cpu_count()
            
        print(f"Starting parallel brute force with {processes} processes")
        
        # Generate all possible passwords upfront (this could be memory intensive)
        passwords = []
        for length in range(min_length, max_length + 1):
            for attempt in itertools.product(charset, repeat=length):
                passwords.append(''.join(attempt))
        
        # Split passwords among processes
        chunk_size = len(passwords) // processes + 1
        password_chunks = [passwords[i:i + chunk_size] for i in range(0, len(passwords), chunk_size)]
        
        with Pool(processes=processes) as pool:
            results = pool.map(self.test_password_chunk, password_chunks)
            
            for i, result in enumerate(results):
                if result:
                    self.found_password = result
                    print(f"Password found: {result}")
                    return True
                    
                self.attempts += len(password_chunks[i])
                if self.attempts % 10000 == 0:
                    print(f"Tested {self.attempts} passwords...")
                    
        return False
    
    def test_password_chunk(self, passwords):
        """Test a chunk of passwords (for parallel processing)"""
        for password in passwords:
            if self.test_password(password):
                return password
        return None
    
    def run(self, attack_type="dictionary", charset="abcdefghijklmnopqrstuvwxyz0123456789", 
            min_length=1, max_length=8, processes=None):
        """Run the brute force attack"""
        start_time = time.time()
        
        if attack_type == "dictionary":
            success = self.dictionary_attack()
        elif attack_type == "bruteforce":
            success = self.brute_force_attack(charset, min_length, max_length)
        elif attack_type == "parallel":
            success = self.parallel_brute_force(charset, min_length, max_length, processes)
        else:
            print(f"Unknown attack type: {attack_type}")
            return False
            
        elapsed_time = time.time() - start_time
        
        if success:
            print(f"Success! Password is: {self.found_password}")
            print(f"Found after {self.attempts} attempts in {elapsed_time:.2f} seconds")
            return True
        else:
            print(f"Failed to find password after {self.attempts} attempts in {elapsed_time:.2f} seconds")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python usb_brute_force.py <drive_path> [options]")
        print("Options:")
        print("  --wordlist <path>    Use dictionary attack with specified wordlist")
        print("  --bruteforce         Use brute force attack")
        print("  --charset <chars>    Character set for brute force (default: a-z0-9)")
        print("  --min-length <n>     Minimum password length (default: 1)")
        print("  --max-length <n>     Maximum password length (default: 8)")
        print("  --parallel           Use parallel processing")
        print("  --processes <n>      Number of processes for parallel attack")
        sys.exit(1)
    
    drive_path = sys.argv[1]
    wordlist_path = None
    attack_type = "dictionary"
    charset = "abcdefghijklmnopqrstuvwxyz0123456789"
    min_length = 1
    max_length = 8
    parallel = False
    processes = None
    
    # Parse command line arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--wordlist" and i + 1 < len(sys.argv):
            wordlist_path = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--bruteforce":
            attack_type = "bruteforce"
            i += 1
        elif sys.argv[i] == "--charset" and i + 1 < len(sys.argv):
            charset = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--min-length" and i + 1 < len(sys.argv):
            min_length = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--max-length" and i + 1 < len(sys.argv):
            max_length = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--parallel":
            parallel = True
            i += 1
        elif sys.argv[i] == "--processes" and i + 1 < len(sys.argv):
            processes = int(sys.argv[i + 1])
            i += 2
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)
    
    if parallel:
        attack
