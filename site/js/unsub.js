var urlParams;
(window.onpopstate = function () {
  var match,
  pl     = /\+/g,
    search = /([^&=]+)=?([^&]*)/g,
      decode = function (s) { return decodeURIComponent(s.replace(pl, " ")); },
        query  = window.location.search.substring(1);

        urlParams = {};
        while (match = search.exec(query))
          urlParams[decode(match[1])] = decode(match[2]);
})();

function submitUnsub() {
  gtag('event', 'unsub', {
    'event_category': 'mainList',
  });

  document.getElementById('unsub-form').style.display = 'none';
  document.getElementById('spinner').style.display = '';

  const id = urlParams.id;
  const address = urlParams.address;

  k8aListSQS.sendMessage({MessageBody: JSON.stringify(['unsubscribe', address, id])}, function (err, data) {
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('unsub-success').style.display = '';
    console.log(err, data);
  });
}
