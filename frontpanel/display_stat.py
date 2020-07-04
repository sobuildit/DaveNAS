import time
import subprocess

from board import SCL, SDA
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import psutil

import RPi.GPIO as GPIO

from vcgencmd import Vcgencmd
vcgm = Vcgencmd()

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

# Create the SSD1306 OLED class
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new("1", (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)

# one-time information grabs
cmd = "dpkg -l | awk '/openmediavault /{ print $3;} '"
omvpkg = subprocess.check_output(cmd, shell=True).decode("utf-8")
print("OMV Version: ", omvpkg)

page=0
ticks = 0

# GPIO setup for front panel button
panelButton = 14
GPIO.setmode(GPIO.BCM)
GPIO.setup(panelButton, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Button pin set as input w/ pull-up
commandState = 0

pushTicks = 0
buttonPressedEvent = 0
buttonReleasedEvent = 0

while True:
	print("Command state: ", commandState)

	# Front panel state machine
	if (commandState == 0):
		# go into command mode after 5 ticks
		if (pushTicks >= 5):
			commandState = 1;
			print("Entered command mode")

	# Look for button release event and check tick count
	elif (commandState == 1):
		print("state 1");
		if (buttonReleasedEvent == 1):
			draw.rectangle((0, 0, width, height), outline=0, fill=0)
			draw.text((x, top + 0), "** Command Mode **", font=font, fill=255)
			disp.image(image)
			disp.show()
			time.sleep(1)
			print("Halt command selected")
			draw.rectangle((0, 0, width, height), outline=0, fill=0)
			draw.text((x, top + 0), "** Command: Halt", font=font, fill=255)
			disp.image(image)
			disp.show()
			commandState = 2 # go to halt selection state

	elif (commandState == 2):
		print("state 2")
		if (pushTicks >= 5):
			print("Halt command issued")
			draw.rectangle((0, 0, width, height), outline=0, fill=0)
			draw.text((x, top + 0), "** HALTING SYSTEM **", font=font, fill=255)
			disp.image(image)
			disp.show()
			# Do it
			subprocess.run("halt")

		elif (buttonReleasedEvent == 1):
			print("Reboot command selected")
			draw.rectangle((0, 0, width, height), outline=0, fill=0)
			draw.text((x, top + 0), "** Command: Reboot", font=font, fill=255)
			disp.image(image)
			disp.show()
			commandState = 3 # go to reboot selection state

	elif (commandState == 3):
		if (pushTicks >= 5):
			print("Reboot command issued")
			draw.rectangle((0, 0, width, height), outline=0, fill=0)
			draw.text((x, top + 0), "** REBOOTING SYSTEM **", font=font, fill=255)
			disp.image(image)
			disp.show()
                        # Do it
			subprocess.run("reboot")

		elif (buttonReleasedEvent == 1):
			print("Cancel command selected")
			draw.rectangle((0, 0, width, height), outline=0, fill=0)
			draw.text((x, top + 0), "** Command: Cancel", font=font, fill=255)
			disp.image(image)
			disp.show()
			commandState = 4 # go to cancel selection state

	elif (commandState == 4):
		if (pushTicks >= 5):
			print("Command mode exited")
			draw.rectangle((0, 0, width, height), outline=0, fill=0)
			disp.image(image)
			disp.show()
			commandState = 0
			pushTicks = 0

	buttonReleasedEvent = 0 # clear button events
	buttonPressedEvent = 0
	if (GPIO.input(panelButton) == 0):
		print("Button pushed")
		if (pushTicks == 0):
			# new press
			print("Button press start")
			buttonPressedEvent = 1
			pushTicks = 1 #  init push counter
		else:
			pushTicks += 1
			print("Pushticks: ",pushTicks)

	else: # reset push counter
		if (pushTicks >= 1):
			buttonReleasedEvent = 1
			print("buttonReleasedEvent")

		buttonPressedEvent = 0
		pushTicks = 0

	if (ticks == 0 and commandState == 0):
	        # Draw  black filled box to clear the image.
		draw.rectangle((0, 0, width, height), outline=0, fill=0)

	        # Shell scripts for system monitoring from here:
	        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load

	        # Page 0 - system information
		if (page == 0):
			# date / time
			cmd = "date +\"%H:%M %d/%m/%Y\""
			date = subprocess.check_output(cmd, shell=True).decode("utf-8")
			print("Date: ", date)

			# uptime
			cmd = "uptime -p"
			uptime = subprocess.check_output(cmd, shell=True).decode("utf-8")

			print("Uptime: ", uptime)

			uptimea, uptimeb = uptime[:len(uptime)//2], uptime[len(uptime)//2:]

			draw.text((x, top + 0), "OMV: " + omvpkg, font=font, fill=255)
			draw.text((x, top + 8), date, font=font, fill=255)
			draw.text((x, top + 16), uptimea, font=font, fill=255)
			draw.text((x, top + 25), uptimeb, font=font, fill=255)


	        # Page 1 - network configuration
		if (page == 1):
	            cmd =  "hostname"
	            hostname = subprocess.check_output(cmd, shell=True).decode("utf-8")

	            net_if_addrs = psutil.net_if_addrs()['eth0'][0]
	            IP = net_if_addrs.address
	            print("IP: ", IP)

	            netmask = net_if_addrs.netmask
	            print("Netmask: ", netmask)

	            cmd = "/sbin/route -n | awk '/UG/{ print $2;} '"
	            gateway = subprocess.check_output(cmd, shell=True).decode("utf-8")
	            print("Gateway: ", gateway)

	            draw.text((x, top + 0), "Host: " + hostname, font=font, fill=255)
	            draw.text((x, top + 8), "IP: " + IP, font=font, fill=255)
	            draw.text((x, top + 16), "GW:" + gateway, font=font, fill=255)
	            draw.text((x, top + 25), "Mask: " + netmask, font=font, fill=255)

	        # Page 2 - storage
		if (page == 2):
			cmd = "df -h | awk '/dev\/sd/{ print $1,\" \",$5;} '"
			disks = subprocess.check_output(cmd, shell=True).decode("utf-8")
			print("Disks: ", disks)
			print("---")
			draw.text((x, top + 0), "Disk Space", font=font, fill=255)
			position = 8

			for disk in disks.splitlines():
				draw.text((x, top + position), disk, font=font, fill=255)
				print(">", disk, "<")
				position += 8

	        # Page 3 - CPU
		if (page == 3):
	            clock = psutil.cpu_freq().current
	            print("clock: ", clock)

	            temp = vcgm.measure_temp()
	            print("temp: ", temp)

	            cpu_usage = psutil.cpu_percent()
	            print("CPU PC: ", cpu_usage)

	            MemUsage = psutil.virtual_memory().percent
	            print("MemUsed: ", MemUsage)

	            draw.text((x, top + 0), "CPU Usage " + str(cpu_usage) + " %", font=font, fill=255)
	            draw.text((x, top + 8), "CPU Temp " + str(temp) + " °C", font=font, fill=255)
	            draw.text((x, top + 16), "CPU Clk " + str(clock) + " MHz", font=font, fill=255)
	            draw.text((x, top + 25), "Mem " + str(MemUsage) + " %", font=font, fill=255)

		page = page + 1
		if (page == 4):
			page = 0

		# Display image.
		disp.image(image)
		disp.show()

    	# manage ticks
	ticks += 1
	if (ticks > 4):
		ticks = 0

	time.sleep(1)
