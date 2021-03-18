Mailcheck.defaultDomains.push('yandex.ru')
// Mailcheck.defaultSecondLevelDomains.push('domain', 'yetanotherdomain') // extend existing SLDs
Mailcheck.defaultTopLevelDomains.push('ru')

// parse the querystring.
// https://stackoverflow.com/a/2880929/1231454
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

function isPossibleEmail(address){
  var re = /^\S+@\S+\.\S+$/	;
  return re.test(address);
}

var lastAddress = null;
var currentSuggestion = null;
function suggestEmail(address, suggestCallback, emptyCallback){
  Mailcheck.run({
    email: address,
    suggested: suggestCallback,
    empty: function() {
      emptyCallback(address);
    },
  });
}

function submitSignup(){
  document.getElementById('invalid-email').style.display = 'none';
  document.getElementById('email-suggestion').style.display = 'none';
  document.getElementById('signup-form').style.display = 'none';
  document.getElementById('spinner').style.display = '';
  document.getElementById('signup-success').style.display = 'none';

  const e = document.getElementById('emailInput');

  if (!isPossibleEmail(e.value)) {
    document.getElementById('invalid-email').style.display = '';
    document.getElementById('email-suggestion').style.display = 'none';
    document.getElementById('signup-form').style.display = '';
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('signup-success').style.display = 'none';
    return;
  }

  suggestEmail(
    e.value,

    function(suggestion) {
      if (currentSuggestion && lastAddress === e.value) {
        gtag('event', 'overrideSuggest', {
          'event_category': 'mainList',
        });
        console.info('overriding', suggestion);
        queueMessage(e.value);
      } else {
        gtag('event', 'suggest', {
          'event_category': 'mainList',
        });
        console.info('suggesting', suggestion);
        currentSuggestion = suggestion.full;
        lastAddress = e.value;
        document.getElementById('invalid-email').style.display = 'none';
        document.getElementById('email-suggestion').innerText = 'Did you mean "' + currentSuggestion + '"? If not, press join again.';
        document.getElementById('email-suggestion').style.display = '';
        document.getElementById('signup-form').style.display = '';
        document.getElementById('spinner').style.display = 'none';
        document.getElementById('signup-success').style.display = 'none';
      } 
    },
    queueMessage, // success
  )
}

function queueMessage(address) {
  const username = document.getElementById('usernameInput').value;
  console.info("sending", address, username);
  gtag('event', 'sub', {
    'event_category': 'mainList',
  });
  k8aListSQS.makeUnauthenticatedRequest('sendMessage', {MessageBody: JSON.stringify(['subscribe', address, null, username])}, function (err, data) {
    document.getElementById('invalid-email').style.display = 'none';
    document.getElementById('email-suggestion').style.display = 'none';
    document.getElementById('signup-form').style.display = 'none';
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('signup-success').innerText = 'You will receive an email at "' + address + '" confirming your subscription.'
    document.getElementById('signup-success').style.display = '';
    console.log(err, data);
  });
}

document.addEventListener("DOMContentLoaded", function() {
  const el = document.getElementById("emailInput");
  if (el) {
    el.addEventListener("keydown", function(e) {
      if (e.keyCode == 13) { submitSignup(); }
    }, false);
  } else {
    console.warn("did not find emailInput");
  }
});
