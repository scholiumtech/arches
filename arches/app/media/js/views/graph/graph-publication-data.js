define([], function() {
    function removeTrailingCommaFromObject(string) {
        return string.replace(/,\s*}*$/, "}");
    }

    const graphPublicationDataHTML = document.querySelector('#graphPublicationData');
    const graphPublicationData = graphPublicationDataHTML.getAttribute('graphPublicationData');

    const parsedGraphPublicationData = JSON.parse(removeTrailingCommaFromObject(graphPublicationData));

    return parsedGraphPublicationData;
});