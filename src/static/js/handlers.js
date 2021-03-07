setInterval("update();", 300);
function update() {
    $('#status-container').load(location.href + " #status-dynamic");
}