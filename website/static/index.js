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


function loadingTagsOnVideo() {
    //Implement code to draw tags from database into this array
IndexTagsArray = ["Politics", "Economy", "Health", "Technology", "Sports"]; 

for(i = 0; i < IndexTagsArray.length; i++) {

document.getElementById("tagList").appendChild(
    elementFromHtml(`<div class="tag">${IndexTagsArray[i]}</div>`)
);

}

}

loadingTagsOnVideo();

