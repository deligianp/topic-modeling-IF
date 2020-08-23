function hexToRgb(hexColorString) {
    if ((hexColorString.length > 5) && (hexColorString.length < 8)) {
        let hexPattern = /^#?([a-f0-9]{2})([a-f0-9]{2})([a-f0-9]{2})$/i;
        let matchResult = hexColorString.match(hexPattern);
        if (matchResult === null) {
            throw "\"" + hexColorString + "\" is not a valid HEX color";
        }
        const baseRed = parseInt(matchResult[1], 16);
        const baseGreen = parseInt(matchResult[2], 16);
        const baseBlue = parseInt(matchResult[3], 16);
        return [baseRed, baseGreen, baseBlue];
    } else if ((hexColorString.length > 2) && (hexColorString < 5)) {
        let hexPattern = /^#?([a-f0-9])([a-f0-9])([a-f0-9])$/i;
        let matchResult = hexColorString.match(hexPattern);
        if (matchResult === null) {
            throw "\"" + hexColorString + "\" is not a valid HEX color";
        }
        const baseRed = 17 * parseInt(matchResult[1], 16);
        const baseGreen = 17 * parseInt(matchResult[2], 16);
        const baseBlue = 17 * parseInt(matchResult[3], 16);
        return [baseRed, baseGreen, baseBlue];
    } else {
        throw "\"" + hexColorString + "\" is not a valid HEX color";
    }
}

function rgbToHex(red, green, blue) {
    let hexChars = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"];
    return "#" + hexChars[Math.floor(red / 16)] + hexChars[Math.floor(red % 16)] + hexChars[Math.floor(green / 16)] + hexChars[Math.floor(green % 16)] + hexChars[Math.floor(blue / 16)] + hexChars[Math.floor(blue % 16)];
}

function colorTints(hexColor, numOfSteps = 1, lighter = true) {
    let rgbColor = hexToRgb(hexColor);
    let steps;
    if (lighter) {
        steps = rgbColor.map(value => (255 - value) / (numOfSteps + 1));
    } else {
        steps = rgbColor.map(value => (value - 0) / (numOfSteps + 1));
    }
    let tints = [rgbColor];
    do {
        tints.push(tints[tints.length - 1].map((color, index) => color + steps[index]));
        numOfSteps--;
    } while (numOfSteps > 0);
    let hexTints = tints.map(tint => rgbToHex(...tint));
    return hexTints;
}

function renderHorizontalLoadingNotification(containerId, loadingImgPath) {
    $("#" + containerId)
        .empty()
        .append($(document.createElement("img"))
            .attr("src", loadingImgPath)
            .attr("class", "w-100")
        );
}

function renderErrorNotification(containerId, heading, message) {
    let $errorPrompt = $(document.createElement("div"))
        .attr("class", "alert alert-danger")
        .append($(document.createElement("h4"))
            .attr("class", "alert-heading")
            .html(heading)
        ).append($(document.createElement("p"))
            .html(message ? message : ""));
    $("#" + containerId).empty().append($errorPrompt);
}

function renderWarningNotification(containerId, heading, message) {
    $("#"+containerId).empty()
        .append($(document.createElement("div"))
            .attr("class", "alert alert-warning")
            .append($(document.createElement("h4"))
                .attr("class","alert-heading")
                .text(heading)
            ).append($(document.createElement("p"))
                .text(message)
            )
        )
}

function renderTopicLinks(tableId, links, labels = null) {
    let $tableBody = $("#" + tableId + " tbody");
    let $tableRow = $(document.createElement("tr"));
    let $tableRowHeading = $(document.createElement("th"))
        .attr("scope", "row")
        .html("Top " + links.length + " topics");
    let $tableRowData = $(document.createElement("td"));
    $.each(links, function (index, link) {
        let $link = $(document.createElement("a"))
            .attr("class", "btn btn-dark btn-sm m-1")
            .attr("href", link)
            .attr("target", "_blank")
            .html(((labels !== null) && (labels.length > index)) ? labels[index] : link);
        $tableRowData.append($link);
    });
    $tableRow.append($tableRowHeading)
        .append($tableRowData);
    $tableBody.append($tableRow);
}

function spawnWindowModal(element) {
    let $element = $(element);

    let $modalWrapper = $(document.createElement("div"))
        .addClass("container-fluid")
        .css("position","absolute")
        .css("top","0")
        .css("left","0")
        .css("bottom","0")
        .css("background-color","rgba(0, 0, 0, 0.5)")
        .append($(document.createElement("div"))
            .addClass("row")
            .addClass("h-100")
            .addClass("align-items-center")
            .addClass("justify-content-center")
            .append($(document.createElement("div"))
                .addClass("col-6")
                .addClass("col-md-3")
                .append($element)
            )
        );
    $("body").append($modalWrapper);
    return $modalWrapper;
}