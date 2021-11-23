var timer;

self.addEventListener('message', function (event) {
    var data = event.data;
    var sec = data['seconds'];
    var status = data['status'];
    switch (status) {
        case 'start':
            timer = setInterval(function () {
                postMessage(sec);
                sec--;
                if (sec < 0) {
                    clearInterval(timer);
                }
            }, 1000);
            break;
        case 'stop':
            clearInterval(timer);
            break;
    }
}, false);