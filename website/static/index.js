
function toggle() {
    document.body.classList.toggle("light");
}

function elementFromHtml(html) {
    const template = document.createElement('template');
    template.innerHTML = html.trim();
    return template.content.firstChild;
}

function fetchVideoData() {
    //Implement code to fetch video data from database
}



loadingTagsOnVideo();

