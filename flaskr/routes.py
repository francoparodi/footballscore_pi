from datetime import datetime
import threading, time, atexit
from flask import current_app as app
from flask import Blueprint, render_template, redirect, url_for, copy_current_request_context

try:
    import RPi.GPIO as GPIO
except (RuntimeError, ModuleNotFoundError):
    import sys
    import fake_rpi
    sys.modules['RPi'] = fake_rpi.RPi     # Fake RPi
    sys.modules['RPi.GPIO'] = fake_rpi.RPi.GPIO # Fake GPIO
    sys.modules['smbus'] = fake_rpi.smbus # Fake smbus (I2C)
    import RPi.GPIO as GPIO
    import smbus

from flask_socketio import SocketIO, emit

socketio = SocketIO()

stop_event = threading.Event()
daemon = threading.Thread()
isDaemonStarted = False
secondsBetweenGPIOStatus = 1
gPIOEvent = False
dictEvents = {'8': 0, '12': 0}

view = Blueprint("view", __name__)

@view.route("/")
def homepage():
    return render_template("homepage.html")

@view.route('/increment/<int:channel>')
def incrementScore(channel):
    dictEvents[str(channel)] = dictEvents[str(channel)] + 1
    on_connect()
    return redirect(url_for("view.homepage"))

@view.route('/decrement/<int:channel>')
def decrementScore(channel):
    dictEvents[str(channel)] = dictEvents[str(channel)] - 1
    on_connect()
    return redirect(url_for("view.homepage"))

@view.route("/reset")
def reset():
    dictEvents['8'] = 0
    dictEvents['12'] = 0
    on_connect()
    return redirect(url_for("view.homepage"))

@socketio.on('connect')
def on_connect():
    name='name'
    channel8 = dictEvents['8']
    channel12 = dictEvents['12']
    socketio.emit('daemonProcess', {'datetime': str(datetime.now()), 'name': name, 'channel8': str(channel8), 'channel12': str(channel12)})

@socketio.on('handleDaemon')
def on_handleDaemon(data):
    global gPIOEvent
    name=data['name']
    action=data['action']

    @copy_current_request_context
    def daemonProcess(name, stop_event):
        # Daemon needed cause emit from button_callback is not allowed
        global gPIOEvent
        while not stop_event.is_set():
            if gPIOEvent:
                channel8 = dictEvents['8']
                channel12 = dictEvents['12']
                socketio.emit('daemonProcess', {'datetime': str(datetime.now()), 'name': name, 'channel8': str(channel8), 'channel12': str(channel12)})
                gPIOEvent = False
            time.sleep(secondsBetweenGPIOStatus)
    
    def button_callback(channel):
        print("Event on channel #" + str(channel))
        global gPIOEvent
        gPIOEvent = True
        dictEvents[str(channel)] = dictEvents[str(channel)] + 1

    global isDaemonStarted
    if action == 'START':
        if not isDaemonStarted:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
            GPIO.setup(8, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 8 to be an input pin 
            GPIO.add_event_detect(8,GPIO.RISING,callback=button_callback, bouncetime=2000) # Setup event on pin 8 rising edge
            GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 12 to be an input pin 
            GPIO.add_event_detect(12,GPIO.RISING,callback=button_callback, bouncetime=2000) # Setup event on pin 12 rising edge
            
            daemon.__init__(target=daemonProcess, args=(name, stop_event), daemon=True)
            daemon.start()
            gPIOEvent = False
            isDaemonStarted = True
    else:
        cleanUp()

def cleanUp():
    print('Safe terminating.')
    GPIO.cleanup()
    stop_event.set()
    global gPIOEvent
    gPIOEvent = False
    global isDaemonStarted
    if(isDaemonStarted):
        daemon.join()
        isDaemonStarted = False
    stop_event.clear()

atexit.register(cleanUp)