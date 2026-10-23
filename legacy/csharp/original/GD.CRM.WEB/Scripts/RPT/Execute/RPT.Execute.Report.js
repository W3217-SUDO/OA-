var rpt = {
    Reset: function () {
        $("#postForm :text").each(function () {
            $(this).val('');
        });

        //$("#SearchCondition_CustomerName").empty();
        //$("#SearchCondition_CustomerName").chosen({
        //    width: '100%',
        //    disable_search: false,
        //    search_contains: true
        //});
    },
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
    CountExecuteCaseGroupByAssistant: function () {
        //var customerNos = $("#SearchCondition_CustomerName").val().join();
        //$("#SearchCondition_CustomerNos").val(customerNos);

        //var courtLawyers = $("#SearchCondition_CourtLawyerName").val().join();
        //$("#SearchCondition_CourtLawyers").val(courtLawyers);

        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/RPT/Report/CountExecuteCaseGroupByAssistant", function (response) {
            if (response.IsSuccess) {
                var r10Lables = [];
                var r10Values = [];
                var r20Lables = [];
                var r20Values = [];
                var r30Lables = [];
                var r30Values = [];
                var r35Lables = [];
                var r35Values = [];
                var r40Lables = [];
                var r40Values = [];
                var r50Lables = [];
                var r50Values = [];
                var r60Lables = [];
                var r60Values = [];
                var r70Lables = [];
                var r70Values = [];
                var r80Lables = [];
                var r80Values = [];
                var r90Lables = [];
                var r90Values = [];
                var r100Lables = [];
                var r100Values = [];

                debugger

                if (response.Data.Execute.R10.Value != null && response.Data.Execute.R10.Value.length > 0) {
                    $.each(response.Data.Execute.R10.Value, function (i, r10) {
                        if (i < 20) {
                            r10Lables.push(r10.Item1);
                            r10Values.push(r10.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r10Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r10Values
                            }
                        ]
                    }

                    $('#execute10').remove();
                    $('#execute10_container').append('<canvas id="execute10" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute10").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R20.Value != null && response.Data.Execute.R20.Value.length > 0) {
                    $.each(response.Data.Execute.R20.Value, function (i, r20) {
                        if (i < 20) {
                            r20Lables.push(r20.Item1);
                            r20Values.push(r20.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r20Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r20Values
                            }
                        ]
                    }

                    $('#execute20').remove();
                    $('#execute20_container').append('<canvas id="execute20" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute20").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R30.Value != null && response.Data.Execute.R30.Value.length > 0) {
                    $.each(response.Data.Execute.R30.Value, function (i, r30) {
                        if (i < 20) {
                            r30Lables.push(r30.Item1);
                            r30Values.push(r30.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r30Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r30Values
                            }
                        ]
                    }

                    $('#execute30').remove();
                    $('#execute30_container').append('<canvas id="execute30" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute30").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R40.Value != null && response.Data.Execute.R40.Value.length > 0) {
                    $.each(response.Data.Execute.R40.Value, function (i, r40) {
                        if (i < 20) {
                            r40Lables.push(r40.Item1);
                            r40Values.push(r40.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r40Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r40Values
                            }
                        ]
                    }

                    $('#execute40').remove();
                    $('#execute40_container').append('<canvas id="execute40" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute40").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R50.Value != null && response.Data.Execute.R50.Value.length > 0) {
                    $.each(response.Data.Execute.R50.Value, function (i, r50) {
                        if (i < 20) {
                            r50Lables.push(r50.Item1);
                            r50Values.push(r50.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r50Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r50Values
                            }
                        ]
                    }

                    $('#execute50').remove();
                    $('#execute50_container').append('<canvas id="execute50" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute50").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R60.Value != null && response.Data.Execute.R60.Value.length > 0) {
                    $.each(response.Data.Execute.R60.Value, function (i, r60) {
                        if (i < 20) {
                            r60Lables.push(r60.Item1);
                            r60Values.push(r60.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r60Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r60Values
                            }
                        ]
                    }

                    $('#execute60').remove();
                    $('#execute60_container').append('<canvas id="execute60" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute60").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R70.Value != null && response.Data.Execute.R70.Value.length > 0) {
                    $.each(response.Data.Execute.R70.Value, function (i, r70) {
                        if (i < 20) {
                            r70Lables.push(r70.Item1);
                            r70Values.push(r70.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r70Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r70Values
                            }
                        ]
                    }

                    $('#execute70').remove();
                    $('#execute70_container').append('<canvas id="execute70" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute70").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R80.Value != null && response.Data.Execute.R80.Value.length > 0) {
                    $.each(response.Data.Execute.R80.Value, function (i, r80) {
                        if (i < 20) {
                            r80Lables.push(r80.Item1);
                            r80Values.push(r80.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r80Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r80Values
                            }
                        ]
                    }

                    $('#execute80').remove();
                    $('#execute80_container').append('<canvas id="execute80" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute80").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R90.Value != null && response.Data.Execute.R90.Value.length > 0) {
                    $.each(response.Data.Execute.R90.Value, function (i, r90) {
                        if (i < 20) {
                            r90Lables.push(r90.Item1);
                            r90Values.push(r90.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r90Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r90Values
                            }
                        ]
                    }

                    $('#execute90').remove();
                    $('#execute90_container').append('<canvas id="execute90" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute90").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Execute.R100.Value != null && response.Data.Execute.R100.Value.length > 0) {
                    $.each(response.Data.Execute.R100.Value, function (i, r100) {
                        if (i < 20) {
                            r100Lables.push(r100.Item1);
                            r100Values.push(r100.Item2);
                        }
                    });

                    var lineChartData1 = {
                        labels: r100Lables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: r100Values
                            }
                        ]
                    }

                    $('#execute100').remove();
                    $('#execute100_container').append('<canvas id="execute100" style="height: 280px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("execute100").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                debugger
                if (AP_PAGE_ID == "30001006")
                {
                    $("#executegridSection3").show();
                    $("#executegridSection2").hide();
                    $("#executegridSection1").hide();
                }
                else if (AP_PAGE_ID == "30001005") {
                    $("#executegridSection3").hide();
                    $("#executegridSection2").show();
                    $("#executegridSection1").hide();
                }
                else if (AP_PAGE_ID == "30001004") {
                    $("#executegridSection3").hide();
                    $("#executegridSection2").hide();
                    $("#executegridSection1").show();
                }
            }
        });
    },
}



