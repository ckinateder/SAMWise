setInterval("update();", 100);
function update() {
    $('#status-container').load(location.href + " #status-dynamic");
}