class RangeSliderTooltip {

    constructor(rangeSliderId) {
        this.rangeSlider = document.getElementById(rangeSliderId);
        if (this.rangeSlider === null) {
            throw "No element in DOM with id \"" + rangeSliderId + "\".";
        }

        // Create custom range slider tooltip
        this.tooltipElement = document.createElement("div");
        this.tooltipElement.classList.add("range-slider-thumb-tooltip");
        this.tooltipElement.id = rangeSliderId + "-tooltip";

        this.rangeSlider.parentNode.insertBefore(this.tooltipElement, this.rangeSlider, this.rangeSlider.nextSibling);

        this.updatePosition()
    }

    updatePosition() {
        let thumbRadius = parseInt(getComputedStyle(document.documentElement).getPropertyValue("--rs-thumb-diameter")) / 2;
        let tooltipRailWidth = this.rangeSlider.clientWidth - 2 * thumbRadius;
        let sliderValue = this.rangeSlider.value / 100;
        this.tooltipElement.style.left = (thumbRadius + (sliderValue * tooltipRailWidth)) + "px";

        let tooltipContent = this._valueMapping(this.rangeSlider.value);
        this.tooltipElement.innerText = "" + tooltipContent;
    }

    _valueMapping = function (sliderValue) {
        return sliderValue;
    };

    set valueMapping(mappingFunction) {
        this._valueMapping = mappingFunction;
        this.updatePosition();
    }
}
