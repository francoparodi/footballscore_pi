function socketIOinit() {
    var socket = io.connect('http://' + document.domain + ':' + location.port);

    socket.on('connect', function() {
        console.log('Websocket connected');
    });

    socket.emit('handleDaemon', {name: '1', action: 'START'});

    socket.on('daemonProcess', function(data) {
        var jStr = JSON.stringify(data);
        var jObj = JSON.parse(jStr);
        var channel8 = jObj.channel8;
        var channel12 = jObj.channel12;
        console.log(jObj.datetime + ' ' + 'Channel8: ' + channel8 + " - Channel12: " + channel12);
        document.getElementById("channel8").innerHTML = channel8;
        document.getElementById("channel12").innerHTML = channel12;
    });
}