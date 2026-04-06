chrome.action.onClicked.addListener(() => {
  chrome.windows.create({
    url: "panel.html",
    type: "popup",
    width: 600,
    height: 900,   // full height on most screens
    left: 0,
    top: 0
  });
});
