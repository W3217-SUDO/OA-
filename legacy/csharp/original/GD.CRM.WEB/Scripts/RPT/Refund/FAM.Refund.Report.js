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
    CountRefundCaseGroupByAssistant: function () {
        //var customerNos = $("#SearchCondition_CustomerName").val().join();
        //$("#SearchCondition_CustomerNos").val(customerNos);

        //var courtLawyers = $("#SearchCondition_CourtLawyerName").val().join();
        //$("#SearchCondition_CourtLawyers").val(courtLawyers);

        $("#postForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/RPT/Report/CountRefundCaseGroupByAssistant", function (response) {
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

               if (response.Data.Refund.R10.Value.length > 0) {
                   $.each(response.Data.Refund.R10.Value, function (i, r10) {
                       if(i < 20)
                       {
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

                    $('#refund10').remove();
                    $('#refund10_container').append('<canvas id="refund10" style="height: 260px; width: 100%;"></canvas>');
                    var ctx = document.getElementById("refund10").getContext("2d");
                    window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
               }

               if (response.Data.Refund.R20.Value.length > 0) {
                   $.each(response.Data.Refund.R20.Value, function (i, r20) {
                       if(i < 20)
                       {
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

                   $('#refund20').remove();
                   $('#refund20_container').append('<canvas id="refund20" style="height: 260px; width: 100%;"></canvas>');
                   var ctx = document.getElementById("refund20").getContext("2d");
                   window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
               }

               if (response.Data.Refund.R30.Value.length > 0) {
                   $.each(response.Data.Refund.R30.Value, function (i, r30) {
                       if(i < 20)
                       {
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

                   $('#refund30').remove();
                   $('#refund30_container').append('<canvas id="refund30" style="height: 260px; width: 100%;"></canvas>');
                   var ctx = document.getElementById("refund30").getContext("2d");
                   window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
               }

               if (response.Data.Refund.R40.Value.length > 0) {
                   $.each(response.Data.Refund.R40.Value, function (i, r40) {
                       if(i < 20)
                       {
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

                   $('#refund40').remove();
                   $('#refund40_container').append('<canvas id="refund40" style="height: 260px; width: 100%;"></canvas>');
                   var ctx = document.getElementById("refund40").getContext("2d");
                   window.myLine = new Chart(ctx).Bar(lineChartData1, { bezierCurve: false, });
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



