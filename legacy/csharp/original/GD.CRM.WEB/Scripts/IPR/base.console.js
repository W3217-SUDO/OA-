(function ($) {

    $.case = {
        getCaseBasicByCaseNo: function (trigger, caseNo, functionCallback) {
            var data = { caseNo: caseNo };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetCaseBasicByCaseNo", data, function (response) {
                //if (response.IsSuccess && response.Data && response.Data != "") {
                setTimeout(functionCallback(response, trigger), 200);
                return false;
                //}
            }, false);
        },
        getCaseBasicByCaseRequestNo: function (trigger, caseRequestNo, functionCallback) {
            var data = { caseRequestNo: caseRequestNo };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetCaseBasicByCaseRequestNo", data, function (response) {
                //if (response.IsSuccess && response.Data && response.Data != "") {
                setTimeout(functionCallback(response, trigger), 200);
                return false;
                //}
            }, false);
        },

        getCaseBasicByCaseNoByOwner: function (trigger, caseNo, functionCallback) {
            var data = { caseNo: caseNo };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetCaseBasicByCaseNoByOwner", data, function (response) {
                //if (response.IsSuccess && response.Data && response.Data != "") {
                setTimeout(functionCallback(response, trigger), 200);
                return false;
                //}
            }, false);
        },
        getCaseBasicByCaseRequestNoByOwner: function (trigger, caseRequestNo, functionCallback) {
            var data = { caseRequestNo: caseRequestNo };
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/IPR/Case/GetCaseBasicByCaseRequestNoByOwner", data, function (response) {
                //if (response.IsSuccess && response.Data && response.Data != "") {
                setTimeout(functionCallback(response, trigger), 200);
                return false;
                //}
            }, false);
        }
    }

    $.caseType = {
        getCaseTypeName: function (caseTypeId) {
            var caseTypeName = '';
            $.each(GV_IPR.CaseTypes, function (i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    caseTypeName = c.CaseTypeName;
                    return false;
                }
            });

            return caseTypeName;
        },
        getCaseTypeListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:750px' id='divCaseFeeTypeList'>"
                + "<div class='i_common_hd'>从下列案件中选择"
                + "<input type='hidden' id='hidCaseTypeId'>"
                + "<input type='hidden' id='hidCaseTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseTypes, function (i, c) {
                html += "<li style='width:200px'><a href='javascript:void(0)' id='" + c.CaseTypeId + "'>" + c.CaseTypeName + "</a></li>";
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },

        getCaseTypeCheckBoxListHtml: function () {
            var html = "<div class='i_common_box'  style='display: none; width:750px'  id='divCaseTypeCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件类型中选择"
                + "<input type='hidden' id='hidCaseTypeId'>"
                + "<input type='hidden' id='hidCaseTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseTypes, function (i, c) {
                html += "<li style='width:180px'><div><input type='checkbox' casetypeid='" + c.CaseTypeId + "' casetypename='" + c.CaseTypeName + "' /><lable>" + c.CaseTypeName + "</lable></div></li>";
            });
            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.lsCaseType = {
        getCaseTypeName: function (caseTypeId) {
            var caseTypeName = '';
            $.each(GV_LS.CaseTypes, function (i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    caseTypeName = c.CaseTypeName;
                    return false;
                }
            });

            return caseTypeName;
        },
        getCaseTypeListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;' id='divCaseFeeTypeList'>"
                + "<div class='i_common_hd'>从下列案件中选择"
                + "<input type='hidden' id='hidCaseTypeId'>"
                + "<input type='hidden' id='hidCaseTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseTypes, function (i, c) {
                html += "<li ><a href='javascript:void(0)' id='" + c.CaseTypeId + "'>" + c.CaseTypeName + "</a></li>";
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },

        getCaseTypeCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;' id='divCaseTypeCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件类型中选择"
                + "<input type='hidden' id='hidCaseTypeId'>"
                + "<input type='hidden' id='hidCaseTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseTypes, function (i, c) {
                html += "<li ><div><input type='checkbox' casetypeid='" + c.CaseTypeId + "' casetypename='" + c.CaseTypeName + "' /><lable>" + c.CaseTypeName + "</lable></div></li>";
            });
            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.caseFileType = {
        getCaseFileTypeName: function (caseTypeId, caseFileTypeId) {
            var caseFileTypeName = '';
            $.each(GV_IPR.CaseTypes, function (i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    $.each(c.CaseFileTypeList, function (j, f) {
                        if (f.FileTypeId == caseFileTypeId) {
                            caseFileTypeName = f.FileTypeName;
                            return false;
                        }
                    });
                }
            });

            return caseFileTypeName;
        },

        getCaseFileTypeNameById: function ( caseFileTypeId) {
            var caseFileTypeName = '';
            $.each(GV_IPR.CaseFileTypes, function (i, f) {
                if (f.FileTypeId == caseFileTypeId) {
                    caseFileTypeName = f.FileTypeName;
                    return false;
                }
            });

            return caseFileTypeName;
        },

        getCaseFileTypeListHtml: function (caseTypeId) {

            if (caseTypeId == 1 || caseTypeId == 2 || caseTypeId == 3 || caseTypeId == 15 || caseTypeId == 16 || caseTypeId == 17)
            {
                caseTypeId = 1;
            
            }
            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseFileTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId) {
                        html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },

        getCaseOfficeFileTypeListHtml: function (caseTypeId) {

            if (caseTypeId == 1 || caseTypeId == 2 || caseTypeId == 3 || caseTypeId == 14 ||caseTypeId == 15 || caseTypeId == 16 || caseTypeId == 17) {
                caseTypeId = 1;

            }
            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseFileTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId && f.IsOfficeFileType) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },

        getCaseNonOfficeFileTypeListHtml: function (caseTypeId) {

            if (caseTypeId == 1 || caseTypeId == 2 || caseTypeId == 3 || caseTypeId == 14  || caseTypeId == 15 || caseTypeId == 16 || caseTypeId == 17) {
                caseTypeId = 1;
            }
            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseFileTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId && f.IsOfficeFileType == false && f.IsTransformed == false) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },



        getAllCaseFileTypeListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_IPR.CaseFileTypes, function (i, f) {
                
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },


        getCaseTransformedFileTypeListHtml: function (caseTypeId) {

            if (caseTypeId == 1 || caseTypeId == 2 || caseTypeId == 3 || caseTypeId == 14  || caseTypeId == 15 || caseTypeId == 16 || caseTypeId == 17) {
                caseTypeId = 1;
            }
            var html = "<div class='i_common_box' style='display: none;  width:650px'  id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseFileTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId && f.IsOfficeFileType == false && f.IsTransformed == true) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },

        getCaseFileTypeCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFileTypeCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseFileTypes, function (i, c) {
                html += "<li style='width:260px'><div><input type='checkbox' casefiletypeid='" + c.FileTypeId + "' casefiletypename='" + c.FileTypeName + "' /><lable>" + c.FileTypeId + c.FileTypeName + "</lable></div></li>";
            });
            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.lsCaseFileType = {
        getCaseFileTypeName: function (caseTypeId, caseFileTypeId) {
            var caseFileTypeName = '';
            $.each(GV_LS.CaseTypes, function (i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    $.each(c.CaseFileTypeList, function (j, f) {
                        if (f.FileTypeId == caseFileTypeId) {
                            caseFileTypeName = f.FileTypeName;
                            return false;
                        }
                    });
                }
            });

            return caseFileTypeName;
        },
        getCaseFileTypeListHtml: function (caseTypeId) {
            var html = "<div class='i_common_box' style='display: none; width:650px'' id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseTypes, function (i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    $.each(c.CaseFileTypeList, function (j, f) {
                        html += "<li style='width:200px' ><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
                    });
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCaseTransformedFileTypeListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;  width:650px'  id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFileTypes, function (i, f) {
                if (f.IsTransformed) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },

        getCaseFileTypeCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFileTypeCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFileTypes, function (i, c) {
                html += "<li style='width:260px'><div><input type='checkbox' casefiletypeid='" + c.FileTypeId + "' casefiletypename='" + c.FileTypeName + "' /><lable>" + c.FileTypeId + c.FileTypeName + "</lable></div></li>";
            });
            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.caseFeeType = {
        getCaseFeeTypeNameById: function (caseFeeTypeId) {
            var caseFeeTypeName = '';
            if (caseFeeTypeId == -100 || caseFeeTypeId == -200 || caseFeeTypeId == -300)
                return caseFeeTypeName;

            $.each(GV_IPR.CaseFeeTypes, function (i, f) {
                if (f.FeeTypeId == caseFeeTypeId) {
                    caseFeeTypeName = f.FeeTypeName;
                    return false;
                }
            });

            return caseFeeTypeName;
        },
        getCaseFeeTypeName: function (caseTypeId,caseFeeTypeId) {
            var caseFeeTypeName = '';
            $.each(GV_IPR.CaseTypes, function (i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    $.each(c.CaseFeeTypeList, function (j, f) {
                        if (f.FeeTypeId == caseFeeTypeId) {
                            caseFeeTypeName = f.FeeTypeName;
                            return false;
                        }
                    });
                }
            });

            return caseFeeTypeName;
        },
 
        getCaseFeeTypeListHtml: function (caseTypeId) {
            var html = "<div class='i_common_box' style='display: none;width:450px' id='divCaseFeeTypeList'>"
                + "<div class='i_common_hd'>从下列费用类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseTypes, function (i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    $.each(c.CaseFeeTypeList, function(j, f) {
                        html += "<li style='width:140px'><a href='javascript:void(0)' id='" + f.FeeTypeId + "'>(" + f.FeeTypeId + ")"+ f.FeeTypeName + "</a></li>";
                    });
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCaseFeeTypeCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:650px' id='divCaseFeeTypeCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件费用类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_IPR.CaseFeeTypes, function (j, f) {
                html += "<li  style='width:200px'><div><input type='checkbox' casefeetypeid='" + f.FeeTypeId + "' casefeetypename='" + f.FeeTypeName + "' /><lable>" + f.FeeTypeName + "</lable></div></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },

        getCaseFeeTypeCheckBoxListHtmlForCaseTypeId: function (classCaseTypeId) {
            var html = "<div class='i_common_box' style='display: none; width:650px' id='divCaseFeeTypeCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件费用类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_IPR.CaseFeeTypes, function (j, f) {

                if (classCaseTypeId == 1) {
                    if ((f.CaseTypeId == 1 || f.CaseTypeId == 2 || f.CaseTypeId == 3) && f.TypeId == 1) {
                        html += "<li  style='width:200px'><div><input type='checkbox' casefeetypeid='" + f.FeeTypeId + "' casefeetypename='" + f.FeeTypeName + "' /><lable>" + f.FeeTypeName + "</lable></div></li>";
                    }
                }
                else if (classCaseTypeId == 2) {
                    if ((f.CaseTypeId == 4) && f.TypeId == 1) {
                        html += "<li  style='width:200px'><div><input type='checkbox' casefeetypeid='" + f.FeeTypeId + "' casefeetypename='" + f.FeeTypeName + "' /><lable>" + f.FeeTypeName + "</lable></div></li>";
                    }
                }
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.lsCaseFeeType = {
        getCaseFeeTypeName: function(caseFeeTypeId) {
            var caseFeeTypeName = '';
            $.each(GV_LS.CaseFeeTypes, function(i, c) {
                if (f.FeeTypeId == caseFeeTypeId) {
                    caseFeeTypeName = f.FeeTypeName;
                    return false;
                }
            });

            return caseFeeTypeName;
        },
        getCaseFeeTypeListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;width:450px' id='divCaseFeeTypeList'>"
                + "<div class='i_common_hd'>从下列费用类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFeeTypes, function (i, f) {
                html += "<li style='width:140px'><a href='javascript:void(0)' id='" + f.FeeTypeId + "'>(" + f.FeeTypeId + ")" + f.FeeTypeName + "</a></li>";
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCaseFeeTypeCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:650px' id='divCaseFeeTypeCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件费用类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_LS.CaseFeeTypes, function (j, f) {
                html += "<li  style='width:200px'><div><input type='checkbox' casefeetypeid='" + f.FeeTypeId + "' casefeetypename='" + f.FeeTypeName + "' /><lable>" + f.FeeTypeName + "</lable></div></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.casePhase = {
        getcasePhaseName: function(caseTypeId, casePhaseId) {
            var casePhaseName = '';
            $.each(GV_IPR.CaseTypes, function(i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    $.each(c.CasePhaseList, function(j, f) {
                        if (f.CasePhaseId == casePhaseId) {
                            casePhaseName = f.CasePhaseName;
                            return false;
                        }
                    });
                }
            });

            return casePhaseName;
        },
        getcasePhaseListHtml: function(caseTypeId) {
            var html = "<div class='i_common_box' style='display: none;' id='divcasePhaseList'>"
                + "<div class='i_common_hd'>从下列案件阶段中选择"
                + "<input type='hidden' id='hidCasePhaseId'>"
                + "<input type='hidden' id='hidCasePhaseName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_IPR.CaseTypes, function(i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    $.each(c.CasePhaseList, function(j, f) {
                        html += "<li><a href='javascript:void(0)' id='" + f.CasePhaseId + "'>" + f.CasePhaseName + "</a></li>";
                    });
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCasePhaseCheckBoxListHtml: function() {
            var html = "<div class='i_common_box' style='display: none; width:750px' id='divCasePhaseCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件阶段中选择"
                + "<input type='hidden' id='hidCasePhaseId'>"
                + "<input type='hidden' id='hidCasePhaseName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            
                $.each(GV_IPR.CasePhaseTypes, function (j, f) {
                    html += "<li  style='width:180px'><div><input type='checkbox' casephaseid='" + f.CasePhaseId + "' casephasename='" + f.CasePhaseName + "' /><lable>" + f.CasePhaseName + "</lable></div></li>";
                });
           
            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.lsCasePhase = {
        getcasePhaseName: function ( casePhaseId) {
            var casePhaseName = '';
            $.each(GV_LS.CasePhaseTypes, function (i, f) {
                if (f.CasePhaseId == casePhaseId) {
                    casePhaseName = f.CasePhaseName;
                    return false;
                }
            });

            return casePhaseName;
        },
        getcasePhaseListHtml: function (caseTypeId) {
            var html = "<div class='i_common_box' style='display: none;' id='divcasePhaseList'>"
                + "<div class='i_common_hd'>从下列案件阶段中选择"
                + "<input type='hidden' id='hidCasePhaseId'>"
                + "<input type='hidden' id='hidCasePhaseName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseTypes, function (i, c) {
                if (c.CaseTypeId == caseTypeId) {
                    $.each(c.CasePhaseList, function (j, f) {
                        html += "<li><a href='javascript:void(0)' id='" + f.CasePhaseId + "'>" + f.CasePhaseName + "</a></li>";
                    });
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCasePhaseCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:750px' id='divCasePhaseCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件阶段中选择"
                + "<input type='hidden' id='hidCasePhaseId'>"
                + "<input type='hidden' id='hidCasePhaseName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_LS.CasePhaseTypes, function (j, f) {
                html += "<li  style='width:180px'><div><input type='checkbox' casephaseid='" + f.CasePhaseId + "' casephasename='" + f.CasePhaseName + "' /><lable>" + f.CasePhaseName + "</lable></div></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }
 
    $.caseFeeInvoiceStatus = {
        getCaseFeeInvoiceStatusCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:550px' id='divCaseFeeInvoiceStatusCheckBoxList'>"
                + "<div class='i_common_hd'>从下列费用状态中选择"
                + "<input type='hidden' id='hidCaseFeeInvoiceStatusId'>"
                + "<input type='hidden' id='hidCaseFeeInvoiceStatusName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_IPR.CaseFeeInvoiceStatus, function (j, f) {
                html += "<li  style='width:150px'><div><input type='checkbox' casefeebillstatusid='" + f.Item2 + "' casefeebillstatusname='" + f.Item1 + "' /><lable>" + f.Item1 + "</lable></div></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.lsCaseFeeInvoiceStatus = {
        getCaseFeeInvoiceStatusCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:550px' id='divCaseFeeInvoiceStatusCheckBoxList'>"
                + "<div class='i_common_hd'>从下列费用状态中选择"
                + "<input type='hidden' id='hidCaseFeeInvoiceStatusId'>"
                + "<input type='hidden' id='hidCaseFeeInvoiceStatusName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_LS.CaseFeeInvoiceStatus, function (j, f) {
                html += "<li  style='width:150px'><div><input type='checkbox' casefeebillstatusid='" + f.Item2 + "' casefeebillstatusname='" + f.Item1 + "' /><lable>" + f.Item1 + "</lable></div></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.lsCaseDetermineTheway = {
        getCaseDetermineThewayCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;' id='divCaseDetermineThewayCheckBoxList'>"
                + "<div class='i_common_hd'>从下列确定方式中选择"
                + "<input type='hidden' id='hidDetermineThewayId'>"
                + "<input type='hidden' id='hidDetermineThewayName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            var determineTheways = [];

            determineTheways.push("营业执照");
            determineTheways.push("发票");
            determineTheways.push("售价");
            determineTheways.push("店招");
            determineTheways.push("名片");

            $.each(determineTheways, function (j, f) {
                html += "<li><div><input type='checkbox' determineThewayname='" + f + "' /><lable>" + f + "</lable></div></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }
    
    $.lsCaseHolderOfRelationship = {

        getCaseHolderOfRelationshipListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;' id='divCaseHolderOfRelationshipList'>"
                + "<div class='i_common_hd'>从下列权利关系中选择"
                + "<input type='hidden' id='hidCaseHolderOfRelationshipId'>"
                + "<input type='hidden' id='hidCaseHolderOfRelationshipName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            var caseHolderOfRelationships = [];

            caseHolderOfRelationships.push("权利人");
            caseHolderOfRelationships.push("独占许可人");
            caseHolderOfRelationships.push("独家许可");
            caseHolderOfRelationships.push("一般许可");
            caseHolderOfRelationships.push("特别授权");
            
            $.each(caseHolderOfRelationships, function (j, f) {
                html += "<li style='width:125px'><a href='javascript:void(0)' caseHolderOfRelationshipName='" + f + "'>" + f + "</a></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },

        getCaseHolderOfRelationshipCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;' id='divCaseHolderOfRelationshipCheckBoxList'>"
                + "<div class='i_common_hd'>从下列权利关系中选择"
                + "<input type='hidden' id='hidCaseHolderOfRelationshipId'>"
                + "<input type='hidden' id='hidCaseHolderOfRelationshipName'>" 
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            var caseHolderOfRelationships = [];

            caseHolderOfRelationships.push("权利人");
            caseHolderOfRelationships.push("独占许可人");
            caseHolderOfRelationships.push("独家许可");
            caseHolderOfRelationships.push("一般许可");
            caseHolderOfRelationships.push("特别授权");

            $.each(caseHolderOfRelationships, function (j, f) {
                html += "<li><div><input type='checkbox' caseHolderOfRelationshipName='" + f + "' /><lable>" + f + "</lable></div></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.lsCaseTheThirdRelationship = {

        getCaseTheThirdRelationshipListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;' id='divCaseTheThirdRelationshipList'>"
                + "<div class='i_common_hd'>从下列关联关系中选择"
                + "<input type='hidden' id='hidCaseTheThirdRelationshipId'>"
                + "<input type='hidden' id='hidCaseTheThirdRelationshipName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            var caseTheThirdRelationships = [];

            caseTheThirdRelationships.push("原告关联系");
            caseTheThirdRelationships.push("被告关联系");
            caseTheThirdRelationships.push("结果关联系");
            caseTheThirdRelationships.push("无关联系");

            $.each(caseTheThirdRelationships, function (j, f) {
                html += "<li style='width:125px'><a href='javascript:void(0)' caseTheThirdRelationshipName='" + f + "'>" + f + "</a></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },

        getCaseTheThirdRelationshipCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;' id='divCaseTheThirdRelationshipCheckBoxList'>"
                + "<div class='i_common_hd'>从下列权利关系中选择"
                + "<input type='hidden' id='hidCaseTheThirdRelationshipId'>"
                + "<input type='hidden' id='hidCaseTheThirdRelationshipName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            var caseTheThirdRelationships = [];

            caseTheThirdRelationships.push("原告关联系");
            caseTheThirdRelationships.push("被告关联系");
            caseTheThirdRelationships.push("结果关联系");
            caseTheThirdRelationships.push("无关联系");

            $.each(caseTheThirdRelationships, function (j, f) {
                html += "<li><div><input type='checkbox' caseTheThirdRelationshipName='" + f + "' /><lable>" + f + "</lable></div></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
    }

    $.caseTaskType = {

        //getCaseTaskTypeListHtml: function () {
        //    var html = "<div class='i_common_box' style='display: none; width:550px' id='divCaseTaskTypeList'>"
        //        + "<div class='i_common_hd'>从下列任务类型中选择"
        //        + "<input type='hidden' id='hidCaseTaskTypeId'>"
        //        + "<input type='hidden' id='hidCaseTaskTypeName'>"
        //        + "</div>"
        //        + "<div class='i_common_bd'>"
        //        + "<ul class='i_common_ul layoutfix'>";

        //    $.each(GV_IPR.CaseTaskTypes, function (j, f) {
        //        html += "<li style='width:125px'><a href='javascript:void(0)' caseTaskTypeName='" + f.TaskTypeName + "'>" + f.TaskTypeName + "</a></li>";
        //    });

        //    html += "</ul>"
        //        + " </div>"
        //        + "</div>";

        //    return html;
        //},


        getCaseTaskTypeListHtml: function (typeId) {
            var html = "<div class='i_common_box' style='display: none; width:550px' id='divCaseTaskTypeList'>"
                + "<div class='i_common_hd'>从下列任务类型中选择"
                + "<input type='hidden' id='hidCaseTaskTypeId'>"
                + "<input type='hidden' id='hidCaseTaskTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            if (typeId == 1 || typeId == 2 || typeId == 3) typeId = 1;

            $.each(GV_IPR.CaseTaskTypes, function (j, f) {
                if (f.CaseTypeId == typeId)
                {
                    html += "<li style='width:125px'><a href='javascript:void(0)' caseTaskTypeName='" + f.TaskTypeName + "'>" + f.TaskTypeName + "</a></li>";
                }
            });

            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },


    }

})(jQuery);

//var messager = {
//    polling: function (show) {
//        var data = {}
//        var messageUrl = AP_ROOT + "2001002/Account/MessageCenter/Index?typeId=1";
//        $.ajaxPostMessage(AP_ROOT + "2001002/Account/MessageCenter/Messages", data, function (response) {
//            if (response.IsSuccess) {
//                if (response.Data.TotalItemCount > 0) {
//                    if (show) {
//                        $.messager.lays(320, 120);
//                        $.messager.show('消息提醒',
//                            '您目前尚有<font color=red>' + response.Data.TotalItemCount + '</font>条通知未处理，请尽快处理！ <a style="color: #06C;" href=' + messageUrl + '  target=_blank>进入处理</a>',
//                            10000);
//                    }

//                    $(".topbar-btn-notice-num").html(response.Data.TotalItemCount);
//                    $(".total-unread-count").html(response.Data.TotalItemCount);

//                    $("ul", ".topbar-notice-body").html('');

//                    var html = '';
//                    $.each(response.Data.Messages, function (i, c) {
//                        html += "<li  class='ng-scope'><a target='_blank' class='clearfix' href='" + messageUrl + "'>"
//                             + "<span class='inline-block'><span class='topbar-notice-link ng-binding' ng-ind='item.title'>" + c.Title
//                             + "</span><span class='topbar-notice-time ng-binding'>" + getDate(convertJsonDateToJSDate(c.SendTime))
//                             + "</span></span><span class='inline-block topbar-notice-class ng-scope' ><span class='topbar-notice-class-name ng-binding'>" + c.TypeName + "</span></span></a></li>";
//                    });

//                    $("ul", ".topbar-notice-body").html(html);

//                } else {
//                    $(".topbar-btn-notice-num").html('0');
//                    $(".total-unread-count").html('0');
//                }
//            }
//        }, false);
//    }
//}

var messager = {
    polling: function (show) {
        var data = {}
        var messageUrl = AP_ROOT + "9001001004/TP/Task/TaskList?typeId=3";
        var taskUrl = AP_ROOT + "9001001004/TP/Task/TaskDetail?taskId=";
        $.ajaxPostMessage(AP_ROOT + "9001001004/TP/Task/GetNewMessageTasks", data, function (response) {
            if (response.IsSuccess) {
                if (response.Data.TotalItemCount > 0) {
                    if (show) {
                        $.messager.lays(320, 120);
                        $.messager.show('任务新消息',
                            '您目前尚有<font color=red>' + response.Data.TotalItemCount + '</font>个任务有消息未查看，请尽快查看！ <a style="color: #06C;" href=' + messageUrl + '  target=_self>进入查看</a>',
                            10000);
                    }

                    $(".topbar-btn-notice-num").html(response.Data.TotalItemCount);
                    $(".total-unread-count").html(response.Data.TotalItemCount);

                    $("ul", ".topbar-notice-body").html('');

                    var html = '';
                    $.each(response.Data.TaskList, function (i, t) {

                        var url = taskUrl + t.TaskId;
                        html += "<li  class='ng-scope'><a target='_blank' class='clearfix' href='" + url + "'>"
                             + "<span class='inline-block'><span class='topbar-notice-link ng-binding' ng-ind='item.title'>" + t.CaseNo + "_" +  t.CustomerName + "_" + t.TaskTitle
                             + "</span><span class='topbar-notice-time ng-binding'>" + getDate(convertJsonDateToJSDate(t.TaskEndTime))
                             + "</span></span><span class='inline-block topbar-notice-class ng-scope' ><span class='topbar-notice-class-name ng-binding'>" + "案件任务" + "</span></span></a></li>";
                    });

                    $("ul", ".topbar-notice-body").html(html);

                } else {
                    $(".topbar-btn-notice-num").html('0');
                    $(".total-unread-count").html('0');
                }
            }
        }, false);
    }
}


function AssociateCaseFileType(div, ctlid, ctlname, caseTypeId, isTransformedFileType, func) {
    //if (!$.isFunction(func)) {
    //    alert("传入的回调方法参数func，不是方法。请检查调用的地方！！");
    //    return;
    //}
     
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.CaseFileType = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;

        var html = '';

        
        $.each(GV_IPR.CaseFileTypes, function (i, f) {
            if (isTransformedFileType) {
                if (f.IsTransformed && (f.FileTypeId.toString().indexOf(name) > -1 || f.FileTypeName.toString().indexOf(name) > -1)) {
                        
                    html += '<a href="javascript:void(0)" fileTypeId=' + f.FileTypeId + ' hedgingFileTypeId="' + f.HedgingFileTypeId + '" hedgingFeeTypeId="' + f.HedgingFeeTypeId + '" >' + f.FileTypeId + f.FileTypeName + '</a>';
                }
            } else {
                   
                if (caseTypeId == null) {
                    if (f.FileTypeId.toString().indexOf(name) > -1 || f.FileTypeName.toString().indexOf(name) > -1) {
                        html += '<a href="javascript:void(0)" fileTypeId=' + f.FileTypeId + ' hedgingFileTypeId="' + f.HedgingFileTypeId + '" hedgingFeeTypeId="' + f.HedgingFeeTypeId + '" >' + f.FileTypeId + f.FileTypeName + '</a>';
                    }
                }
                else {

                    if (caseTypeId == 1 || caseTypeId == 2 || caseTypeId == 3 || caseTypeId == 15 || caseTypeId == 16 || caseTypeId == 17)
                    {
                        caseTypeId = 1;
                    }

                    if (f.CaseTypeId == caseTypeId && (f.FileTypeId.toString().indexOf(name) > -1 || f.FileTypeName.toString().indexOf(name) > -1)) {
                        html += '<a href="javascript:void(0)" fileTypeId=' + f.FileTypeId + ' hedgingFileTypeId="' + f.HedgingFileTypeId + '" hedgingFeeTypeId="' + f.HedgingFeeTypeId + '" >' + f.FileTypeId + f.FileTypeName + '</a>';
                    }
                }

            }
        });
         

        $(div).find(".i_common_list").html(html);
        $(div).find(".i_common_list a").click(function () {
            $(ctlid).val($(this).attr("fileTypeId"));
            $(ctlname).val($(this).text());
            var caseFileTypeId = $(this).attr("fileTypeId");
            var caseFileTypeNameText = $(this).text();
            var hedgingFileTypeId = $(this).attr("hedgingFileTypeId");
            var hedgingFeeTypeId = $(this).attr("hedgingFeeTypeId");

            if (func != null) {
                func(caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId, hedgingFeeTypeId);
            }

            $(div).hide();
        });

        //$.ajaxPost( AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaeFileTypeList", curobj, function (response) {
        //    $(div).find(".i_common_list").empty();
        //    if (response.IsSuccess) {
        //        if (response.Data) {
        //            var html = "";
        //            $.each(response.Data.Customers, function (i, c) {
        //                html += '<a href="javascript:void(0)" customerid=' + c.CustomerId + ' >' + c.CustomerName + '</a>';
        //            });

        //            $(div).find(".i_common_list").html(html);
        //            $(div).find(".i_common_list a").click(function () {
        //                $(ctlid).val($(this).attr("customerId"));
        //                $(ctlname).val($(this).text());
        //                $(div).hide();
        //            });
        //        }
        //    }
        //    else {
        //        $.showModalMessageBox(response.Message);
        //    }
        //}, false);
        $(div).css({
            "position": "absolute",
            "left": $(ctlname).offsetParent().position().left + 15,
            "top": $(ctlname).offsetParent().position().top + 32,
            "z-index": 9999
        }).show();
    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.CaseFileType(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
    });

    return this;
}

function AssociateUser(div, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.CaseUserName = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var html = '';
        var data = { userName: name };
        $.ajaxPostMessage( AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/Users", data, function(response) {
            if (response.IsSuccess) {
                $.each(response.Data, function (i, c) {
                    html += '<a href="javascript:void(0)" userId=' + c.Item1 + '>' + c.Item2 + '</a>';
                });

                $(div).find(".i_common_list").html(html);
                $(div).find(".i_common_list a").click(function () {
                    $(ctlid).val($(this).attr("userId"));
                    $(ctlname).val($(this).text());
                    $(div).hide();
                });

                $(div).css({
                    "position": "absolute",
                    "left": $(ctlname).position().left +2,
                    "top": $(ctlname).position().top + 26,
                    "z-index": 9999
                }).show();
            }
        },false);


    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.CaseUserName(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
    });

    return this;
}

function AssociateAvailableUser(div, ctlid, ctlname, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.CaseUserName = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = name;

        var html = '';
        var data = { userName: name };
        $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/Account/UserCenter/AvailableUsers", data, function (response) {
            if (response.IsSuccess) {
                $.each(response.Data, function (i, c) {
                    html += '<a href="javascript:void(0)" userId=' + c.Item1 + '>' + c.Item2 + '</a>';
                });

                $(div).find(".i_common_list").html(html);
                $(div).find(".i_common_list a").click(function () {
                    $(ctlid).val($(this).attr("userId"));
                    $(ctlname).val($(this).text());
                    $(div).hide();
                });

                $(div).css({
                    "position": "absolute",
                    "left": $(ctlname).position().left + 2,
                    "top": $(ctlname).position().top + 26,
                    "z-index": 9999
                }).show();
            }
        }, false);


    }

    $(ctlname).bind('keyup', { obj: this }, function (event) {
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.CaseUserName(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
    });

    return this;
}

function setsidebarnav(e) {
    if ($(e).hasClass("sidebar-nav-active")) {

        $(e).removeClass("sidebar-nav-active");
        
        $(e).find("ul").css("max-height", "0px");

        if ($(".sidebar-title-icon", e).hasClass("icon-arrow-right")) {
            $(".sidebar-title-icon", e).removeClass("icon-arrow-right");
            $(".sidebar-title-icon", e).addClass("icon-arrow-down");
        } else {
            $(".sidebar-title-icon", e).removeClass("icon-arrow-down");
            $(".sidebar-title-icon", e).addClass("icon-arrow-right");
        }

    } else {
        $(e).addClass("sidebar-nav-active");
        $(e).find("ul").removeAttr("style");

        if ($(".sidebar-title-icon", e).hasClass("icon-arrow-right")) {
            $(".sidebar-title-icon", e).removeClass("icon-arrow-right");
            $(".sidebar-title-icon", e).addClass("icon-arrow-down");
        } else {
            $(".sidebar-title-icon", e).removeClass("icon-arrow-down");
            $(".sidebar-title-icon", e).addClass("icon-arrow-right");
        }
    }
}

function setacesidebarnav(e) {
    if ($(e).hasClass("active open")) {
        $(e).removeClass("active open");
        $(e).find("ul[name='first-ul']").removeClass("nav-show");
        $(e).find("ul[name='first-ul']").addClass("nav-hide");
        $(e).find("ul[name='first-ul']").css("display", "none");
    }
    else {
        $(e).addClass("active open");
        $(e).find("ul[name='first-ul']").removeClass("nav-hide");
        $(e).find("ul[name='first-ul']").addClass("nav-show");
        $(e).find("ul[name='first-ul']").css("display", "block");
    }
}

$(document).ready(function () {

    $(function () { $("[data-toggle='tooltip']").tooltip(); });

    if ($("li.nav-item.ng-scope.active").length) {

        var linvaid = $("li.nav-item.ng-scope.active").attr("li-nva-id");
        var trigger = $("li.nav-item.ng-scope.active").parents().find(".sidebar-nav")[linvaid];

        //setsidebarnav(trigger);

        //jQuery(trigger).click();
    }

    messager.polling(false);
    setInterval("messager.polling(true)", 6000*5);//半分钟刷新1次

    $(window).keydown(function (e) {
        if (e.which == 13) {
            jQuery("#btnSearchGo").click();
        }
    });

    $("#btnNavigation").click(function () {
        if ($("#divNavigationTopbar").hasClass("open")) {
            $("#divNavigationTopbar").removeClass("open");
            $("#divNavigationTopbar").removeClass("active");
            $("#divNavigationPanel").css("display", "none");
        } else {
            $("#divNavigationTopbar").addClass("open");
            $("#divNavigationPanel").css("display", "block");
        }
        $(this).stopPropagation();
    });

    $(".dropdown-menu-logout").off().on("click", function () {
        widow.location = AP_ROOT + 'Home/Logout';
    });

 

    $(".sidebar-fold").click(function () {
        if ($(this).hasClass("icon-unfold")) {
            $(this).removeClass("icon-unfold");
            $(this).addClass("icon-fold");
            $(".viewFramework-body").removeClass("viewFramework-sidebar-full");
            $(".viewFramework-body").addClass("viewFramework-sidebar-mini");
        
        } else {
            $(this).removeClass("icon-fold");
            $(this).addClass("icon-unfold");
            $(".viewFramework-body").removeClass("viewFramework-sidebar-mini");
            $(".viewFramework-body").addClass("viewFramework-sidebar-full");
        }
    });

    $(".sidebar-title").click(function () {
        setsidebarnav(this.parentElement);
    });

    $("#ace-dropdown-toggle").off().on("click", function () {
        setacesidebarnav(this.parentElement);
    });


    $(".sidebar-toggle").click(function () {
        if ($("#sidebar").hasClass("menu-min")) {
            $("#sidebar").removeClass("menu-min");
            $(".viewFramework-body").removeClass("viewFramework-sidebar-mini");
           
            $(".viewFramework-body").addClass("viewFramework-sidebar-full");
            $("#sidebar-collapse-i").removeClass("fa-angle-double-right");
            $("#sidebar-collapse-i").addClass("fa-angle-double-left");
        }
        else {
            $("#sidebar").addClass("menu-min");
            $(".viewFramework-body").removeClass("viewFramework-sidebar-full");
            $(".viewFramework-body").addClass("viewFramework-sidebar-mini");
            $("#sidebar-collapse-i").removeClass("fa-angle-double-left");
            $("#sidebar-collapse-i").addClass("fa-angle-double-right");

        }

        //if ($(this).hasClass("icon-unfold")) {
        //    $(this).removeClass("icon-unfold");
        //    $(this).addClass("icon-fold");
        //    $(".viewFramework-body").removeClass("viewFramework-sidebar-full");
        //    $(".viewFramework-body").addClass("viewFramework-sidebar-mini");

        //} else {
        //    $(this).removeClass("icon-fold");
        //    $(this).addClass("icon-unfold");
        //    $(".viewFramework-body").removeClass("viewFramework-sidebar-mini");
        //    $(".viewFramework-body").addClass("viewFramework-sidebar-full");
        //}
    });
   

    $("#btnSearch").click(function () {
        if ($(".topbar-search-dropdown").hasClass("ng-hide")) {
            $(".topbar-search-dropdown").removeClass("ng-hide");
        } else {
            $(".topbar-search-dropdown").addClass("ng-hide");
        }
    });

    $("#btnAdvancedSearch").click(function () {

        $("#Search_SearchConditionId").val('');
        
        $(".caseadvancedsearch").css('display','block');
        $('#caseSearchModal').modal({ backdrop: 'static', keyboard: false });
        
        if (searchCondition) {
            searchCondition.Init();
            if (typeof (GV_IPRSearch) != "undefined" && GV_IPRSearch.Condition != null) {
                searchCondition.InitCaseSearchCondition(GV_IPRSearch.Condition);
            }
        }

        if ($(".topbar-search-dropdown").hasClass("ng-hide")) {
            $(".topbar-search-dropdown").removeClass("ng-hide");
        } else {
            $(".topbar-search-dropdown").addClass("ng-hide");
        }
        //window.location =  AP_ROOT + AP_PAGE_ID + "/IPR/Case/CaseList";
    });

    $("#btnSearchGo").click(function () {
        var k = $("#txtKeyword").val().trim();
        if (k == '') {
            return false;
        }
        var regd = /^.*[\\\'\"<>|-—]+.*$/;
        if (regd.test(k)) {
            $.showModalMessageBox("禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
            return false;
        }

        var search = {};

        search.CaseId = 0;
        search.PageId = '1001001999';
        search.PageNo = 1;
        search.PageSize = 100;
        search.PageName = "页面搜索";
        search.Keyword = k;

        var url = AP_ROOT + "1001001001/IPR/Case/CreateUpdate?typeId=1&caseId=0&k=" + escape(JSON.stringify(search));
        window.location = url;
    });

    $(".viewFramework-product-navbar-collapse").off().on("click", function () {
        if ($(".viewFramework-product").hasClass("viewFramework-product-col-1")) {
            $(".viewFramework-product").removeClass("viewFramework-product-col-1");
            $(".icon-collapse-left").css("display", "none");
            $(".icon-collapse-right").css("display", "block");
        } else {
            $(".viewFramework-product").addClass("viewFramework-product-col-1");
            $(".icon-collapse-left").css("display", "block");
            $(".icon-collapse-right").css("display", "none");
        }
    });

    $(".viewFramework-product-navbar-collapse-3").off().on("click", function () {
        if ($(".viewFramework-product").hasClass("viewFramework-product-col-3")) {
            $(".viewFramework-product").removeClass("viewFramework-product-col-3");
            $(".icon-collapse-left").css("display", "none");
            $(".icon-collapse-right").css("display", "block");
        } else {
            $(".viewFramework-product").addClass("viewFramework-product-col-3");
            $(".icon-collapse-left").css("display", "block");
            $(".icon-collapse-right").css("display", "none");
        }
    });
});

 