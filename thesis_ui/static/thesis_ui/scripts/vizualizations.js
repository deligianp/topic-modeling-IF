class ArticleTopicsPieChart{
    
    constructor(canvasId, urlBase, colorPalette=null) {
        this.canvasId=canvasId;
        this.urlBase=urlBase;
        this.colorPalette = colorPalette == null ? ["#333333", "#999999"] : colorPalette;
    }

    render(topics) {
        let remainingPieArea=100;
        let labels=[];
        let values=[];
        let links={};
        let colors=[];

        topics.forEach( (element,index) => {
            let topicLabel="Topic "+element.topic;
            labels.push(topicLabel);
            let roundedValue=parseFloat((element.value * 100).toFixed(2));
            values.push(roundedValue);
            remainingPieArea-=roundedValue;
            links[topicLabel]=this.urlBase+element.topic;
            colors.push(this.colorPalette[index%this.colorPalette.length]);
        });
        
        values.push(remainingPieArea);
        labels.push("Rest of topics");

        let canvasElement = document.getElementById(this.canvasId);
        // Creating pie chart inside element with the id defined when creating the object
        let pieChart=new Chart(canvasElement, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    label: labels,
                    data: values,
                    backgroundColor: colors
                }]
            },
            options: {
                legend: {
                    position: 'right'
                },
                tooltips: {
                    enabled: true,
                    mode:'single',
                    callbacks:{
                        label: function (tooltipItem, data) {
                            var index = tooltipItem.index;
                            return data.labels[index] + ': ' + data.datasets[0].data[index] + "%";
                        }
                    }
                }
            }
        });
        this.chart=pieChart;

        // Adding listener for the clicks on the pie sectors
        canvasElement.addEventListener("click",function(event){
            let slice = pieChart.getElementAtEvent(event);
            if (!slice.length) return; // return if not clicked on slice
            let label = slice[0]._model.label;
            if (links.hasOwnProperty(label)) window.open(links[label]);
        });

        this.labels=labels;
        this.values=values;
        this.links=labels.map(label => links[label]);
        this.colors=colors;
    }
}