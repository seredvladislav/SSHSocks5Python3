# Run as:
python python ssh_socks.py -ssh {ssh_host} -P {ssh_port} -N -v -l {ssh_user} -pw {ssh_password} -D 127.0.0.1:7000
# Make exe on Windows:      
pip install -r requirements_frozen.txt     
## pyinstaller (recommended):
pyinstaller ssh_socks.spec    