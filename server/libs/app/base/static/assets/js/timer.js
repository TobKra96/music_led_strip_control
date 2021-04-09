var timer;

self.addEventListener('message', function(event) {
    var data = event.data;
    var sec = data['seconds'];
    switch (data['status']) {
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
    };
}, false);