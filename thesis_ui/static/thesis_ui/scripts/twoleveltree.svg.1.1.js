class NodeTooltip {
    heading;
    text;

    constructor(width, maxHeight, axisX, orientation = "right", scrollX = false, scrollY = true, offsetY = 0, spawnVisible = false) {
        this.element = document.createElementNS("http://www.w3.org/2000/svg", "foreignObject");
        this.element.setAttribute("width", parseInt(width) + "px");
        this.element.setAttribute("height", maxHeight+"px");
        this.options = {};
        this.options.rightOrientation = orientation === "right";
        this.options.offsetY = offsetY;
        this.element.setAttribute("x", this.options.rightOrientation ? axisX : axisX - width);
        this.element.setAttribute("y", this.options.offsetY);

        //Append tooltip div
        let tooltipDiv = document.createElement("div");
        tooltipDiv.style.width = "100%";
        tooltipDiv.style.height = "auto";
        tooltipDiv.style.padding = "5px";
        tooltipDiv.style.backgroundColor = "rgba(0, 0, 0, 0.9)";
        tooltipDiv.style.color = "white";
        tooltipDiv.style.overflowX = scrollX ? "auto" : "visible";
        tooltipDiv.style.overflowY = scrollY ? "auto" : "visible";
        tooltipDiv.style.maxHeight = parseInt(maxHeight) + "px";
        tooltipDiv.style.textAlign = "left";
        this.element.appendChild(tooltipDiv);
        this.tooltipDiv = tooltipDiv;

        this.element.style.display = spawnVisible ? "block" : "none";
        this.element.style.overflow = "visible";

        this.heading = "";
        this.text = "";
    }

    hide() {
        this.element.style.display = "none";
    }

    show() {
        this.element.style.display = "block";
    }

    setHeading(heading) {
        if (heading !== null) {
            let innerString = heading.outerHTML;
            if (innerString === undefined) {
                innerString = heading.toString();
            }
            this.heading = innerString;
            this.renderTooltipDiv();
            // Notify listeners ?
            return;
        }
        throw "Can't set heading with null";
    }

    setText(text) {
        if (text !== null) {
            let innerString = text.outerHTML;
            if (innerString === undefined) {
                innerString = text.toString();
            }
            this.text = innerString;
            this.renderTooltipDiv();
            return;
        }
        throw "Can't set text with null";
    }

    getHeading() {
        return this.heading;
    }

    getText() {
        return this.text;
    }

    renderTooltipDiv() {
        this.tooltipDiv.innerHTML = "";
        let headingDiv = document.createElement("div");
        let textDiv = document.createElement("div");
        headingDiv.innerHTML = this.heading;
        textDiv.innerHTML = this.text;
        this.tooltipDiv.appendChild(headingDiv);
        this.tooltipDiv.appendChild(textDiv);
        if (this.heading !== "" && this.text !== "") {
            textDiv.style.borderTop = "solid 1px white";
        } else {
            textDiv.style.borderTop = "none";
        }
    }

    resetContent() {
        this.setHeading("");
        this.setText("");
    }

    bindNode(node) {
        if (node !== null) {
            if (node.hasOwnProperty("y")) {
                this.element.setAttribute("y", parseInt(node.y) + this.options.offsetY);
            } else {
                throw "Not a valid Node object was given";
            }
        } else {
            throw "No nodes were given";
        }
    }
}


class TwoLevelTree {

    data = [];
    nodes = [];
    links = [];
    parents = {
        __length__: 0
    };
    parentsOrderedSequence = [];
    childrenOrderedSequence = [];
    children = {
        __length__: 0
    };

    svg = null;
    parentElement = null;
    tooltip0 = null;
    tooltip1 = null;

    presentation = {
        firstLevelLabel: "First level",
        secondLevelLabel: "Second level",

        svgAspectRatio: null,
        minimumHeight: null,
        drawHeight: null,
        nodeR: null,
        tooltipHeight: null,
        treeTextSize: null,
        xPos0: null,
        xPos1: null,
        yDistance0: null,
        yDistance1: null,

        primaryColor: "#007bff",
        primaryColorEvent: "#003D80",
        primaryColorMuted: "#80BDFF",
        highlightBackground: "#003d80",
        highlightTextColor: "#fff",
        secondaryColor: "#7f00ff",
        secondaryColorEvent: "#b27fe6",
        linkColor: "#000",
        linkColorMuted: "#c3c3c3"
    };

    activeNode0 = null;
    activeNode1 = null;
    hoveredNode = null;

    nodeHighlight = node => node.hasOwnProperty("highlight") ? node.highlight : false;

    nodeLabel = node => node.hasOwnProperty("label") ? node.label : node.name;

    nodeText = node => node.hasOwnProperty("text") ? node.text.join("<br>") : "";

    linkLabel = link => link.hasOwnProperty("label") ? link.label : null;

    nodeTooltip = function (node) {
        let tooltip = node.depth == 0 ? this.tooltip0 : this.tooltip1;
        tooltip.resetContent();
        let heading = this.nodeLabel(node);
        let text = this.nodeText(node);
        tooltip.setHeading(heading);
        tooltip.setText(text);
        tooltip.bindNode(node);
        return tooltip;
    }

    constructor(parentId, svgAspectRatio) {
        this.svg = null;
        // Check whether parent element with given ID exists. Failure to find the element will result in an error
        if (!(this.parentElement = document.getElementById(parentId))) {
            throw "No element was found with id \"" + parentId + "\"";
        }
        this.presentation.svgAspectRatio = svgAspectRatio;
    }


    parseTree() {
        let tree = this;
        this.data.forEach(function (parentDefinition) {
            if ((parentDefinition.hasOwnProperty("name")) && (parentDefinition.hasOwnProperty("associations"))) {
                if (!(parentDefinition.name in tree.parents)) {
                    let parentData = {};
                    parentData.name = parentDefinition.name;
                    parentData.children = parentDefinition.associations.map(function (associationDefinition) {
                        let childDefinition = associationDefinition.child;
                        let childData;
                        if (childDefinition.hasOwnProperty("name")) {
                            if (!(childDefinition.name in tree.children)) {
                                childData = {};
                                childData.name = childDefinition.name;
                                childData.x = 0;
                                childData.y = 0;
                                childData.depth = 1;
                                childData.associatedNodes = [];
                                childData.associatedNodes.push(parentData);
                                let excludeProperties = ["name"];
                                for (let key in childDefinition) {
                                    if (childDefinition.hasOwnProperty(key) && (!(childData.hasOwnProperty(key))) && (!(excludeProperties.includes(key)))) {
                                        childData[key] = childDefinition[key];
                                    }
                                }
                                tree.children[childData.name] = childData;
                                tree.children["__length__"] += 1;
                                if (childData.highlight) {
                                    tree.childrenOrderedSequence.unshift(childData.name);
                                } else {
                                    tree.childrenOrderedSequence.push(childData.name);
                                }
                                tree.nodes.push(childData);
                            } else {
                                childData = tree.children[childDefinition.name];
                                childData.associatedNodes.push(parentData);
                            }
                            let link = {source: parentData, target: childData};
                            let excludeProperties = ["child"];
                            for (let key in associationDefinition) {
                                if (associationDefinition.hasOwnProperty(key) && (!(link.hasOwnProperty(key))) && (!(excludeProperties.includes(key)))) {
                                    link[key] = associationDefinition[key];
                                }
                            }
                            tree.links.push(link);
                            return childData;
                        } else {
                            throw "A child definition misses a required property: name";
                        }
                    });
                    parentData.x = 0;
                    parentData.y = 0;
                    parentData.depth = 0;
                    parentData.associatedNodes = parentData.children;
                    let excludeProperties = ["name", "associations"];
                    for (let key in parentDefinition) {
                        if (parentDefinition.hasOwnProperty(key) && (!(parentData.hasOwnProperty(key))) && (!(excludeProperties.includes(key)))) {
                            parentData[key] = parentDefinition[key];
                        }
                    }
                    tree.parents[parentData.name] = parentData;
                    tree.parents["__length__"] += 1;
                    if (parentData.highlight)  {
                        tree.parentsOrderedSequence.unshift(parentData.name);
                    }
                    else {
                        tree.parentsOrderedSequence.push(parentData.name);
                    }
                    tree.nodes.push(parentData);
                    return parentData;
                } else {
                    throw "Multiple definitions for parent with name " + parentDefinition.name;
                }
            } else {
                if (!(parentDefinition.hasOwnProperty("name"))) {
                    throw "A parent definition misses a required property: name";
                } else {
                    throw "A parent definition misses a required property: associations";
                }
            }
        });
    }

    updateData(data) {
        // Store new data to be visualized
        this.data = data;
        this.nodes = [];
        this.links = [];
        this.parents = {
            __length__: 0
        };
        this.children = {
            __length__: 0
        };
	this.parentsOrderedSequence=[];
	this.childrenOrderedSequence=[];
        // Read the input JSON and fill the corresponding fields that the class uses
        this.parseTree();
        // Initialize the SVG and paint the required elements
        this.visualize();
    }

    svgMaxWidth() {
        let parentElementComputedStyle = getComputedStyle(this.parentElement);
        let paddingX = parseFloat(parentElementComputedStyle.paddingLeft) + parseFloat(parentElementComputedStyle.paddingRight);
        return this.parentElement.clientWidth - paddingX - 2 * (this.parentElement.offsetWidth - this.parentElement.clientWidth);
    }

    initSVG() {
        let svgMaxWidth = this.svgMaxWidth();
        let svgElement = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svgElement.setAttribute("id", this.parentElement.id + "-svg");
        svgElement.setAttribute("width", svgMaxWidth + "px");
        this.svg = {
            element: svgElement,
            width: svgMaxWidth
        }
    }

    visualize() {
        let tree = this;
        // If there is another SVG already assigned to this class, remove it from DOM
        // (That's the case when visualize is being called when data is updated)
        if ((this.svg != null) && (this.svg.element !== null)) {
            this.svg.element.remove();
        }
        // Create new SVG element equal to the width of the parent div
        this.initSVG();
        this.parentElement.appendChild(this.svg.element);
        // let width = parseInt(d3.select(this.svg).style("width"));
        // this.presentation.minimumHeight = parseInt(d3.select(this.svg).style("height"));
        // this.presentation.drawHeight = parseInt(d3.select(this.svg).style("height"));
        this.presentation.nodeR = Math.ceil(parseFloat(this.svg.width) * 0.01);
        this.presentation.xPos0 = Math.floor(parseFloat(this.svg.width) * 0.25);
        this.presentation.xPos1 = Math.floor(parseFloat(this.svg.width) * 0.75);
        this.presentation.tooltipHeight = Math.floor(parseFloat(this.svg.width) * 0.3);
        this.presentation.treeTextSize = this.presentation.nodeR * 2;
        this.calculateLayout();
        this.paintTree();

        window.addEventListener("resize", function (event) {
            let newWidth = tree.svgMaxWidth();
            let newHeight = newWidth * tree.presentation.svgAspectRatio;
            tree.resizeSVG(newWidth, newHeight);
            // if (tree.activeNode0 !== null) {
            //     tree.tooltip0.setWidth(parseInt(0.2 * newWidth));
            // }
        })
    }

    calculateNodeY() {
        // Based on the reshaped SVG, distribute the space between each node of each tree layer
        // xDistance0 is the distance between each node for layer0
        // xDistance1 is the distance between each node for layer1
        this.yDistance0 = Math.floor((this.svg.height - (this.parents.__length__ * 2 * this.presentation.nodeR) - this.presentation.tooltipHeight) / (this.parents.__length__));
        this.yDistance1 = Math.floor((this.svg.height - (this.children.__length__ * 2 * this.presentation.nodeR) - this.presentation.tooltipHeight) / (this.children.__length__));
        let tree=this;

        // For each parent skip xDistance0 pixels + the sum of diameters of any previously placed nodes + the radius for the current node
        let parentIndex = 0;
        tree.parentsOrderedSequence.forEach(function(parentName){
            tree.parents[parentName].y = ((parentIndex + 1) * tree.yDistance0) + (parentIndex * 2 * tree.presentation.nodeR) + tree.presentation.nodeR;
            parentIndex += 1;
        });

        // For each child skip xDistance1 pixels + the sum of diameters of any previously placed nodes + the radius for the current node
        let childIndex = 0;
        tree.childrenOrderedSequence.forEach(function(childName){
            tree.children[childName].y = ((childIndex + 1) * tree.yDistance1) + (childIndex * 2 * tree.presentation.nodeR) + tree.presentation.nodeR;
            childIndex += 1;
        });
    }

    calculateNodeX() {
        // Set each parent's y to the level's yPosition
        for (let key in this.parents) {
            if (key !== "__length__" && this.parents.hasOwnProperty(key)) {
                this.parents[key].x = this.presentation.xPos0;
            }
        }
        // Set each child's y to the level's yPosition
        for (let key in this.children) {
            if (key !== "__length__" && this.children.hasOwnProperty(key)) {
                this.children[key].x = this.presentation.xPos1;
            }
        }
    }

    resizeSVG(width, height) {
        this.svg.element.setAttribute("width", width);
        this.svg.element.setAttribute("height", height);
        this.svg.width = width;
        this.svg.height = height;
    }

    calculateLayout() {
        // Find which tree level has the most nodes
        let maxNumberOfNodes = Math.max(this.parents.__length__, this.children.__length__);
        // Calculate the required height in order to be able to visualize the tree level with the biggest length
        let verticalMargin = this.presentation.nodeR * 2;
        let requiredHeight = maxNumberOfNodes * ((2 * this.presentation.nodeR) + verticalMargin) + this.presentation.tooltipHeight;
        // Extend SVG height to match the required height
        this.resizeSVG(this.svg.width, requiredHeight);
        this.presentation.svgAspectRatio = requiredHeight / this.svg.width;
        this.svg.element.setAttribute("viewBox", "0 0 " + this.svg.width + " " + this.svg.height);
        this.calculateNodeX();
        // Given the new SVG height, distribute along X the nodes.
        // Note: it is assumed that because of the previous call of calculateNodeY, all nodes have been placed on ther respective tree depth
        this.calculateNodeY();
    }

    linkNodes() {
        let discoveredPaths = [];
        for (let key in this.parents) {
            if (key !== "length" && this.parents.hasOwnProperty(key)) {
                let source = this.parents[key];
                for (let key in source.children) {
                    if (key !== "length" && source.children.hasOwnProperty(key)) {
                        let target = source.children[key];
                        let link = {source: source, target: target};
                        discoveredPaths.push(link);
                        source.associatedLinks.push(link);
                        target.associatedLinks.push(link);
                    }
                }
            }
        }
        this.links = discoveredPaths;
    }

    paintTree() {
        let tree = this;

        this.links.forEach(function (link) {
            let source = link.source;
            let target = link.target;

            let levelDifference = Math.abs(target.x - source.x);
            let controlPointsDistance = levelDifference * 0.25;

            let pathElement = document.createElementNS("http://www.w3.org/2000/svg", "path");
            pathElement.setAttribute("d", "M " + (source.x + tree.presentation.nodeR) + " " + source.y + " C " + (target.x - controlPointsDistance) + " " + source.y + " " + (source.x + controlPointsDistance) + " " + target.y + " " + (target.x - tree.presentation.nodeR) + " " + target.y);
            pathElement.setAttribute("fill", "none");
            pathElement.setAttribute("stroke", "black");
            pathElement.setAttribute("stroke-width", "1");
            let pathId = source.name + "-" + target.name;
            pathElement.setAttribute("id", pathId);
            tree.svg.element.appendChild(pathElement);
            link.pathElement = pathElement;

            let pathLabelElement = document.createElementNS("http://www.w3.org/2000/svg", "text");
            pathLabelElement.setAttribute("dy", -4);
            pathLabelElement.setAttribute("id", pathId + "-label");
            pathLabelElement.style.display = "none";

            let pathLabelTextElement = document.createElementNS("http://www.w3.org/2000/svg", "textPath");
            pathLabelTextElement.setAttribute("href", "#" + pathId);
            pathLabelTextElement.setAttribute("startOffset", "50%");
            let labelContent = tree.linkLabel(link);
            pathLabelTextElement.innerHTML = labelContent;

            pathLabelElement.appendChild(pathLabelTextElement);
            tree.svg.element.appendChild(pathLabelElement);
            link.pathLabelElement = pathLabelElement;
        });

        this.nodes.forEach(function (node) {
            // let nodeGElement = document.createElement("g");
            let nodeCircleElement = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            nodeCircleElement.setAttribute("class", "node");
            nodeCircleElement.setAttribute("id", (node.depth == 0 ? "s-" : "t-") + node.name);
            nodeCircleElement.setAttribute("cx", node.x);
            nodeCircleElement.setAttribute("cy", node.y);
            nodeCircleElement.setAttribute("fill", tree.presentation.primaryColor);
            nodeCircleElement.setAttribute("r", tree.presentation.nodeR);
            nodeCircleElement.__data__ = node;
            tree.svg.element.appendChild(nodeCircleElement);
            node.circleElement = nodeCircleElement;

            // Append text
            let nodeLabelElement = document.createElementNS("http://www.w3.org/2000/svg", "text");
            nodeLabelElement.setAttribute("id", "s-" + node.name + "-label");
            nodeLabelElement.setAttribute("text-anchor", node.depth == 0 ? "end" : "start");
            nodeLabelElement.setAttribute("font-family", "\"Lucida Console\", Monaco, monospace, monospace");
            nodeLabelElement.setAttribute("font-size", tree.presentation.treeTextSize);
            nodeLabelElement.setAttribute("font-weight", tree.nodeHighlight(node) ? "bold" : "start");
            nodeLabelElement.setAttribute("fill", tree.nodeHighlight(node) ? tree.presentation.highlightTextColor : "gray");
            nodeLabelElement.setAttribute("dominant-baseline", "middle");
            nodeLabelElement.setAttribute("x", node.depth === 0 ? node.x - (tree.presentation.nodeR + 2) : node.x + (tree.presentation.nodeR + 2));
            nodeLabelElement.setAttribute("y", node.y);
            let nodeLabelElementContent = tree.nodeLabel(node);
            if (nodeLabelElementContent.length > 12) {
                nodeLabelElement.innerHTML = "<title>" + nodeLabelElementContent + "</title>" + nodeLabelElementContent.substring(0, 9) + "...";
            } else {
                nodeLabelElement.innerHTML = nodeLabelElementContent;
            }
            tree.svg.element.appendChild(nodeLabelElement);

            if (node.highlight) {
                let nodeLabelBBox = nodeLabelElement.getBBox()
                let contrastBox = document.createElementNS("http://www.w3.org/2000/svg", "rect")
                contrastBox.setAttribute("x", nodeLabelBBox.x-1);
                contrastBox.setAttribute("y", nodeLabelBBox.y-2);
                contrastBox.setAttribute("rx","2");
                contrastBox.setAttribute("width", nodeLabelBBox.width+2);
                contrastBox.setAttribute("height", nodeLabelBBox.height+4);
                contrastBox.setAttribute("fill", tree.presentation.highlightBackground);
                tree.svg.element.insertBefore(contrastBox, nodeLabelElement);
            }

            node.labelElement = nodeLabelElement;
            node.circleElement.addEventListener("mouseover", function () {
                if (((node.depth == 0) && (tree.activeNode0 == null)) || ((node.depth == 1) && (tree.activeNode1 == null))) {
                    node.circleElement.setAttribute("fill", tree.presentation.primaryColorEvent);
                }
            });
            node.circleElement.addEventListener("mouseout", function () {
                if (((node.depth == 0) && (tree.activeNode0 == null)) || ((node.depth == 1) && (tree.activeNode1 == null))) {
                    node.circleElement.setAttribute("fill", tree.presentation.primaryColor);
                }
            });
            node.circleElement.addEventListener("click", function () {
                tree.registerActiveNode(node);
            })
        });

        this.tooltip0 = new NodeTooltip(
            this.presentation.xPos0 * 0.8,
            this.presentation.tooltipHeight,
            this.presentation.xPos0 - (this.presentation.nodeR + 1),
            "left",
            true,
            true,
            -this.presentation.nodeR,
            false
        );

        this.tooltip1 = new NodeTooltip(
            this.presentation.xPos0 * 0.8,
            this.presentation.tooltipHeight,
            this.presentation.xPos1 + this.presentation.nodeR + 1,
            "right",
            true,
            true,
            -this.presentation.nodeR,
            false
        );
        this.svg.element.appendChild(this.tooltip0.element);
        this.svg.element.appendChild(this.tooltip1.element);

        // Finally register all nodes that may have been activated but a repaint was called
        if (tree.activeNode0 !== null) {
            tree.registerNode(tree.activeNode0);
        }
        if (tree.activeNode1 !== null) {
            tree.registerNode(tree.activeNode1);
        }
    }

    registerActiveNode(node) {
        let oldNode;
        if (node.depth == 0) {
            oldNode = this.activeNode0;
            if (this.activeNode0 != null) {
                this.unregisterActiveNode(this.activeNode0);
            }
            if (oldNode !== node) {
                this.registerNode(node);
            }
        } else {
            if (node.depth == 1) {
                oldNode = this.activeNode1;
                if (this.activeNode1 != null) {
                    this.unregisterActiveNode(this.activeNode1);
                }
                if (oldNode !== node) {
                    this.registerNode(node);
                }
            }
        }
    }

    registerNode(nodeData) {
        let tree = this;
        let nodeIdPrefix = nodeData.depth == 0 ? "s-" : "t-";
        let levelCircleElements = document.querySelectorAll("circle[id^='" + nodeIdPrefix + "']");
        let targetCircleElement = document.querySelector("#" + nodeIdPrefix + nodeData.name);
        levelCircleElements.forEach(function (circleElement) {
            if (circleElement !== targetCircleElement) {
                circleElement.setAttribute("fill", tree.presentation.primaryColorMuted);
            }
        })
        targetCircleElement.setAttribute("fill", this.presentation.primaryColorEvent);
        if (nodeData.depth === 0) {
            this.activeNode0 = nodeData;
        } else {
            this.activeNode1 = nodeData;
        }
        let tooltip = this.nodeTooltip(nodeData);
        tooltip.show();

        if ((this.activeNode0 !== null) && (this.activeNode1 !== null)) {
            this.links.forEach(function (link) {
                if (link.pathElement.id !== tree.activeNode0.name + "-" + tree.activeNode1.name) {
                    link.pathElement.setAttribute("stroke", "rgba(192,192,192,0.5)");
                } else {
                    link.pathElement.setAttribute("stroke-width", "3px");
                    link.pathLabelElement.style.display = "block";
                }
            });
        }
    }

    unregisterActiveNode(node) {
        let tree = this;
        if ((this.activeNode0 !== null) && (this.activeNode1 !== null)) {
            this.links.forEach(function (link) {
                if (link.pathElement.id !== tree.activeNode0.name + "-" + tree.activeNode1.name) {
                    link.pathElement.setAttribute("stroke", "black");
                } else {
                    link.pathElement.setAttribute("stroke-width", "1");
                    link.pathLabelElement.style.display = "none";
                }
            });
        }
        let nodeIdPrefix = node.depth === 0 ? "s-" : "t-";
        document.querySelectorAll("circle[id^='" + nodeIdPrefix + "']").forEach(function (node) {
            node.setAttribute("fill", tree.presentation.primaryColor);
        });
        if (node.depth === 0) {
            this.activeNode0 = null;
            this.tooltip0.hide();
            this.tooltip0.resetContent();
        } else {
            this.activeNode1 = null;
            this.tooltip1.hide();
            this.tooltip1.resetContent();
        }
    }
}
