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
    CountRoiGroupByCustomer: function () {
        var customerNos = $("#SearchCondition_CustomerName").val().join();
        $("#SearchCondition_CustomerNos").val(customerNos);

        var courtLawyers = $("#SearchCondition_CourtLawyerName").val().join();
        $("#SearchCondition_CourtLawyers").val(courtLawyers);

        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/RPT/Report/CountRoiGroupByCustomer", function (response) {
            if (response.IsSuccess) {
                var cycleLables = [];
                var cycleValues = [];
                var rateLabels = [];
                var rateVaues = [];
                var deficitLabels = [];
                var deficitValues = [];
                var deficitRateValues = [];

                if (response.Data.Roi.Cycle.length > 0) {
                    $.each(response.Data.Roi.Cycle, function (i, cycle) {
                        cycleLables.push(cycle.Item2);
                        cycleValues.push(cycle.Item3);
                    });

                    var lineChartData1 = {
                        labels: cycleLables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: cycleValues
                            }
                        ]
                    }

                    $('#roi1').remove();
                    $('#roi1_container').append('<canvas id="roi1" style="height: 260px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("roi1").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Roi.Rate.length > 0) {
                    $.each(response.Data.Roi.Rate, function (i, roiRate) {
                        rateLabels.push(roiRate.Item2);
                        if (roiRate.Item4 == 0) {
                            rateVaues.push(100);
                        }
                        else {
                            rateVaues.push(((roiRate.Item5 * 0.15 - roiRate.Item3) / roiRate.Item4 / roiRate.Item6) * 365 * 100);
                        }
                    });

                    var lineChartData4 = {
                        labels: rateLabels,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: rateVaues
                            }
                        ]
                    }

                    $('#roi4').remove();
                    $('#roi4_container').append('<canvas id="roi4" style="height: 260px; width: 100%;"></canvas>');
                    var ctx4 = document.getElementById("roi4").getContext("2d");
                    //ctx4.clearRect(0, 0, 1448, 750); // 清空画布
                    window.myLine = new Chart(ctx4).Bar(lineChartData4, { bezierCurve: false, });
                }

                if (response.Data.Roi.Deficit.length > 0) {
                    $.each(response.Data.Roi.Deficit, function (i, deficit) {
                        deficitLabels.push(deficit.Item2);
                        deficitValues.push(deficit.Item3);
                        if (deficit.Item4 == 0) {
                            deficitRateValues.push(0);
                        }
                        else {
                            deficitRateValues.push((deficit.Item3 / deficit.Item4) * 100);
                        }
                    });

                    var lineChartData2 = {
                        labels: deficitLabels,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: deficitValues
                            }
                        ]
                    }

                    $('#roi2').remove();
                    $('#roi2_container').append('<canvas id="roi2" style="height: 260px; width: 100%;"></canvas>');
                    var ctx2 = document.getElementById("roi2").getContext("2d");
                    window.myLine = new Chart(ctx2).Bar(lineChartData2, { bezierCurve: false, });

                    var lineChartData3 = {
                        labels: deficitLabels,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: deficitRateValues
                            }
                        ]
                    }

                    $('#roi3').remove();
                    $('#roi3_container').append('<canvas id="roi3" style="height: 260px; width: 100%;"></canvas>');
                    var ctx3 = document.getElementById("roi3").getContext("2d");
                    window.myLine = new Chart(ctx3).Bar(lineChartData3, { bezierCurve: false, });

                }
            }
        });

    },
    CountRoiGroupByStaff: function () {
        var staffs = $("#SearchCondition_CountStaffName").val().join();
        $("#SearchCondition_CountRoiGroupStaffs").val(staffs);

        var customerNos = $("#SearchCondition_CustomerName").val().join();
        $("#SearchCondition_CustomerNos").val(customerNos);

        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/RPT/Report/CountRoiGroupByStaff", function (response) {
            if (response.IsSuccess) {

                var cycleLables = [];
                var cycleValues = [];

                var rateLabels = [];
                var rateVaues = [];

                var deficitLabels = [];
                var deficitValues = [];
                var deficitRateValues = [];

                if (response.Data.Roi.Cycle.length > 0) {
                    $.each(response.Data.Roi.Cycle, function (i, cycle) {
                        cycleLables.push(cycle.Item2);
                        cycleValues.push(cycle.Item3);
                    });

                    var lineChartData1 = {
                        labels: cycleLables,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: cycleValues
                            }
                        ]
                    }

                    $('#roi1').remove();
                    $('#roi1_container').append('<canvas id="roi1" style="height: 260px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("roi1").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
                }

                if (response.Data.Roi.Rate.length > 0) {

                    $.each(response.Data.Roi.Rate, function (i, roiRate) {
                        debugger
                        rateLabels.push(roiRate.Item2);

                        if (roiRate.Item4 == 0) {
                            rateVaues.push(100);
                        }
                        else {
                            rateVaues.push(((roiRate.Item5 * 0.15 - roiRate.Item3)/ roiRate.Item4 / roiRate.Item6) * 365 * 100);
                        }
                    });
 
                    var lineChartData4 = {
                        labels: rateLabels,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: rateVaues
                            }
                        ]
                    }

                    $('#roi4').remove();
                    $('#roi4_container').append('<canvas id="roi4" style="height: 260px; width: 100%;"></canvas>');
                    var ctx4 = document.getElementById("roi4").getContext("2d");
                    ctx4.clearRect(0, 0, 1448, 750); // 清空画布
                    window.myLine = new Chart(ctx4).Bar(lineChartData4, { bezierCurve: false, });
                }

                if (response.Data.Roi.Deficit.length > 0) {
                    $.each(response.Data.Roi.Deficit, function (i, deficit) {
                        deficitLabels.push(deficit.Item2);
                        deficitValues.push(deficit.Item3);
                        if (deficit.Item4 == 0) {
                            deficitRateValues.push(0);
                        }
                        else {
                            deficitRateValues.push((deficit.Item3 / deficit.Item4) * 100);
                        }      
                    });

                    var lineChartData2 = {
                        labels: deficitLabels,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: deficitValues
                            }
                        ]
                    }

                    $('#roi2').remove();
                    $('#roi2_container').append('<canvas id="roi2" style="height: 260px; width: 100%;"></canvas>');
                    var ctx2 = document.getElementById("roi2").getContext("2d");
                    window.myLine = new Chart(ctx2).Bar(lineChartData2, { bezierCurve: false, });

                    var lineChartData3 = {
                        labels: deficitLabels,
                        datasets: [
                            {
                                fillColor: "seagreen",
                                data: deficitRateValues
                            }
                        ]
                    }

                    $('#roi3').remove();
                    $('#roi3_container').append('<canvas id="roi3" style="height: 260px; width: 100%;"></canvas>');
                    var ctx3 = document.getElementById("roi3").getContext("2d");
                    window.myLine = new Chart(ctx3).Bar(lineChartData3, { bezierCurve: false, });
                  
                }
            }
        });

    },
}



