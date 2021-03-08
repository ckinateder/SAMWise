setInterval("update();", 1000);
function update() {
    $('#status-container').load(location.href + " #status-dynamic");
}