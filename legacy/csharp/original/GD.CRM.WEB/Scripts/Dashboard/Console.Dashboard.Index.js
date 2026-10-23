var dashboard = {

    ResetSize: function () {
        //if ($("#divTaskList").length > 0) {
        //    $("#divTaskList").css("height", $(window).height() - $("#divTaskList").offset().top - 10);
        //}
        //if ($("#divCasePatentOfficeFileList").length > 0) {
        //    $("#divCasePatentOfficeFileList").css("height", $(window).height() - $("#divCasePatentOfficeFileList").offset().top - 10);
        //}
        //if ($("#divCaseList").length > 0) {
        //    $("#divCaseList").css("height", $(window).height() - $("#divCaseList").offset().top - 10);
        //}
    },

    Layout: function () {
        $.ajaxPost(AP_ROOT + "Console/Dashboard/Dashboard", null, function (response) {
            if (response.IsSuccess) {
                
                var doughnutData = [
                        {
                            value: response.Data.CaseType_110_Counts,
                            color: "#F7464A",
                            highlight: "#FF5A5E",
                            label: "立案待分配"
                        },
                        {
                            value: response.Data.CaseType_120_Counts,
                            color: "#46BFBD",
                            highlight: "#5AD3D1",
                            label: "文书准备"
                        },
                        {
                            value: response.Data.CaseType_130_Counts,
                            color: "#FDB45C",
                            highlight: "#FFC870",
                            label: "一审"
                        },
                        {
                            value: response.Data.CaseType_140_Counts,
                            color: "#8775a7",
                            highlight: "#7775a7",
                            label: "二审"
                        },

                        {
                            value: response.Data.CaseType_150_Counts,
                            color: "#949FB1",
                            highlight: "#A8B3C5",
                            label: "再审"
                        },

                        {
                            value: response.Data.CaseType_160_Counts,
                            color: "#333333",
                            highlight: "#A8B3C5",
                            label: "执行"
                        }
                ];

                try {
                    
                    var ctx = document.getElementById("Canvas1").getContext("2d");
                    window.myDoughnut = new Chart(ctx).Doughnut(doughnutData, { responsive: false });
                }
                catch (e)
                {
                    
                    console.log(e);
                }
 

                var randomScalingFactor = function () { return Math.round(Math.random() * 100) };

                var dt = new Date();

                var lineChartData = {
                    labels: [
                              response.Data.To10DayCaseCounts[0] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[0].Item1)),
                              response.Data.To10DayCaseCounts[1] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[1].Item1)),
                              response.Data.To10DayCaseCounts[2] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[2].Item1)),
                              response.Data.To10DayCaseCounts[3] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[3].Item1)),
                              response.Data.To10DayCaseCounts[4] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[4].Item1)),
                              response.Data.To10DayCaseCounts[5] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[5].Item1)),
                              response.Data.To10DayCaseCounts[6] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[6].Item1)),
                              response.Data.To10DayCaseCounts[7] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[7].Item1)),
                              response.Data.To10DayCaseCounts[8] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[8].Item1)),
                              response.Data.To10DayCaseCounts[9] == null ? getDate(dt) : getDate(convertJsonDateToJSDate(response.Data.To10DayCaseCounts[9].Item1))
                    ],
                    datasets: [
                        {
                            fillColor: "rgba(220,220,220,0.2)",
                            strokeColor: "rgba(220,220,220,1)",
                            pointColor: "rgba(220,220,220,1)",
                            pointStrokeColor: "#fff",
                            pointHighlightFill: "#fff",
                            pointHighlightStroke: "rgba(220,220,220,1)",
                            data: [
                               response.Data.To10DayCaseCounts[0] == null ? 0 : response.Data.To10DayCaseCounts[0].Item2,
                               response.Data.To10DayCaseCounts[1] == null ? 0 : response.Data.To10DayCaseCounts[1].Item2,
                               response.Data.To10DayCaseCounts[2] == null ? 0 : response.Data.To10DayCaseCounts[2].Item2,
                               response.Data.To10DayCaseCounts[3] == null ? 0 : response.Data.To10DayCaseCounts[3].Item2,
                               response.Data.To10DayCaseCounts[4] == null ? 0 : response.Data.To10DayCaseCounts[4].Item2,
                               response.Data.To10DayCaseCounts[5] == null ? 0 : response.Data.To10DayCaseCounts[5].Item2,
                               response.Data.To10DayCaseCounts[6] == null ? 0 : response.Data.To10DayCaseCounts[6].Item2,
                               response.Data.To10DayCaseCounts[7] == null ? 0 : response.Data.To10DayCaseCounts[7].Item2,
                               response.Data.To10DayCaseCounts[8] == null ? 0 : response.Data.To10DayCaseCounts[8].Item2,
                               response.Data.To10DayCaseCounts[9] == null ? 0 : response.Data.To10DayCaseCounts[9].Item2
                            ]
                        }
                    ]
                }

                try {
                    var ctx = document.getElementById("Canvas2").getContext("2d");
                    
                    window.myLine = new Chart(ctx).Line(lineChartData, {
                        bezierCurve: false,
                    });
                }
                catch (e)
                {
                    console.log(e);
                }
    

                //var lineChartData = {
                //    labels: [response.Data.CaseAnnualYearCounts[0].Item1,
                //             response.Data.CaseAnnualYearCounts[1].Item1,
                //             response.Data.CaseAnnualYearCounts[2].Item1,
                //             response.Data.CaseAnnualYearCounts[3].Item1,
                //             response.Data.CaseAnnualYearCounts[4].Item1,
                //             response.Data.CaseAnnualYearCounts[5].Item1,
                //             response.Data.CaseAnnualYearCounts[6].Item1,
                //             response.Data.CaseAnnualYearCounts[7].Item1,
                //             response.Data.CaseAnnualYearCounts[8].Item1,
                //             response.Data.CaseAnnualYearCounts[9].Item1,
                //             response.Data.CaseAnnualYearCounts[10].Item1,
                //             response.Data.CaseAnnualYearCounts[11].Item1],
                //    datasets: [
                //        {
                //            fillColor: "seagreen",
                //            data: [
                //                 response.Data.CaseAnnualYearCounts[0].Item2,
                //                 response.Data.CaseAnnualYearCounts[1].Item2,
                //                 response.Data.CaseAnnualYearCounts[2].Item2,
                //                 response.Data.CaseAnnualYearCounts[3].Item2,
                //                 response.Data.CaseAnnualYearCounts[4].Item2,
                //                 response.Data.CaseAnnualYearCounts[5].Item2,
                //                 response.Data.CaseAnnualYearCounts[6].Item2,
                //                 response.Data.CaseAnnualYearCounts[7].Item2,
                //                 response.Data.CaseAnnualYearCounts[8].Item2,
                //                 response.Data.CaseAnnualYearCounts[9].Item2,
                //                 response.Data.CaseAnnualYearCounts[10].Item2,
                //                 response.Data.CaseAnnualYearCounts[11].Item2]
                //        }
                //    ]
                //}
                //var ctx = document.getElementById("Canvas3").getContext("2d");
                //window.myLine = new Chart(ctx).Bar(lineChartData, { bezierCurve: false, });

            }
        });
    },
}

$(document).ready(function () {
    dashboard.Layout();
    dashboard.ResetSize();

    $(window).resize(function () {
        dashboard.ResetSize();
    });
});
