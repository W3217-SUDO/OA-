(function ($) {

    $.case = {
        ViewCaseId: function (e, caseId, caseNo) {

            $(e).parents("tr").css("background", "yellow");
            $(e).parents("tr").toggleClass("selected_tr");
            var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
            addtabs(url, caseNo);
            //window.open(url);
        },
        View: function (caseNo) {
            var url = AP_ROOT + AP_PAGE_ID + "/Legal/Case/CaseView?caseNo=" + caseNo;
            addtabs(url, caseNo);
            //window.open(url);
        },
        Search: function (k) {
            debugger
          
            if (k == '') {
                return false;
            }
            var regd = /^.*[\\\'\"<>|-—]+.*$/;
            if (regd.test(k)) {
                $.showModalMessageBox("禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }
            var url = AP_ROOT + "1001001001/Legal/CaseList/List?k=" + escape(k);
            window.location = url;
        }
    }

    $.lsGroupId = {
        Lawfirm: 10, //律所
        Trad: 20     //平台
    },

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

            if (caseTypeId == 1 || caseTypeId == 2 || caseTypeId == 3 || caseTypeId == 15 || caseTypeId == 16 || caseTypeId == 17) {
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

            if (caseTypeId == 1 || caseTypeId == 2 || caseTypeId == 3 || caseTypeId == 15 || caseTypeId == 16 || caseTypeId == 17) {
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

            if (caseTypeId == 1 || caseTypeId == 2 || caseTypeId == 3 || caseTypeId == 15 || caseTypeId == 16 || caseTypeId == 17) {
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
            $.each(GV_LS.CaseFileTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId) {
                    html += "<li style='width:200px' ><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
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

        getCaseOfficeFileTypeListHtml: function (caseTypeId) {
 
            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFileTypes, function (i, f) {
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

            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFileTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFileTypeId'>"
                + "<input type='hidden' id='hidCaseFileTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFileTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId && f.IsOfficeFileType == false && f.IsTransformed == false) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FileTypeId + "' text='" + f.FileTypeName + "' hedgingFeeTypeId='" + f.HedgingFeeTypeId + "' hedgingFileTypeId='" + f.HedgingFileTypeId + "'>" + f.FileTypeId + f.FileTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
    }

    $.caseFeeType = {
        TypeId: {
            OfficeFee: 1,
            NonOfficeFee:2,
            CommissionFee: 3
        },
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

        TypeId: {
            OfficeFee: 1,
            NonOfficeFee: 2,
            CommissionFee: 3,
            Nonparty: 5,
        },
        getCaseFeeTypeName: function(caseFeeTypeId) {
            var caseFeeTypeName = '';
            $.each(GV_LS.CaseFeeTypes, function(i, f) {
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
        getCaseInternalFeeTypeCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none; width:650px' id='divCaseFeeTypeCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件费用类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_LS.CaseFeeTypes, function (j, f) {
                if ( f.TypeId == 4) {
                    html += "<li  style='width:200px'><div><input type='checkbox' casefeetypeid='" + f.FeeTypeId + "' casefeetypename='" + f.FeeTypeName + "' /><lable>" + f.FeeTypeName + "</lable></div></li>";
                }
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
        getCaseOfficeFeeTypeListHtml: function (caseTypeId) {
            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFeeTypeList'>"
                + "<div class='i_common_hd'>从下列官费类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFeeTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId && f.TypeId == 1) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FeeTypeId + "' typeId='" + f.TypeId + "' text='"
                        + f.FeeTypeName + "'>" + f.FeeTypeId + f.FeeTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCaseNonOfficeFeeTypeListHtml: function (caseTypeId) {

            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFeeTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFeeTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId &&  f.TypeId == 2) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FeeTypeId + "' typeId='" + f.TypeId + "' text='" + f.FeeTypeName
                         + "'>" + f.FeeTypeId + f.FeeTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCaseOtherFeeTypeListHtml: function (caseTypeId) {

            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFeeTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFeeTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId && f.TypeId == 3) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FeeTypeId + "' typeId='" + f.TypeId + "' text='" + f.FeeTypeName
                         + "'>" + f.FeeTypeId + f.FeeTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCaseInternalFeeTypeListHtml: function (caseTypeId) {

            var html = "<div class='i_common_box' style='display: none; width:850px' id='divCaseFeeTypeList'>"
                + "<div class='i_common_hd'>从下列文档类型中选择"
                + "<input type='hidden' id='hidCaseFeeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeTypeId'>"
                + "<input type='hidden' id='hidCaseFeeTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";
            $.each(GV_LS.CaseFeeTypes, function (i, f) {
                if (f.CaseTypeId == caseTypeId && f.TypeId == 4) {
                    html += "<li style='width:200px'><a href='javascript:void(0)' id='" + f.FeeTypeId + "' typeId='" + f.TypeId + "' text='" + f.FeeTypeName
                         + "'>" + f.FeeTypeId + f.FeeTypeName + "</a></li>";
                }
            });
            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
        getCaseFeeTypeListTreeHtml: function () {
            var setting = {
                view: {
                    showLine: false,
                },
                check: {
                    enable: true,
                    chkStyle: "checkbox",
                    radioType: "all"
                },

                callback: {
                    onClick: $.lsCaseFeeType.zTreeOnClick,
                },
                data: {
                    simpleData: {
                        enable: true
                    }
                }
            };

            var zNodes = [];

            var pnode1 = {};
            pnode1.id = 1;
            pnode1.pId = 1;
            pnode1.name = "官费";
            pnode1.open = true;
            zNodes.push(pnode1);

            var pnode2 = {};
            pnode2.id = 2;
            pnode2.pId = 2;
            pnode2.name = "代理费";
            pnode2.open = false;
            zNodes.push(pnode2);

            var pnode3 = {};
            pnode3.id = 3;
            pnode3.pId = 3;
            pnode3.name = "其他费用";
            pnode3.open = false;
            zNodes.push(pnode3);

            var pnode4 = {};
            pnode4.id = 4;
            pnode4.pId = 4;
            pnode4.name = "内部费用";
            pnode4.open = false;
            zNodes.push(pnode4);

            var pnode5 = {};
            pnode5.id = 5
            pnode5.pId = 5;
            pnode5.name = "第三方费用";
            pnode5.open = false;
            zNodes.push(pnode5);


            $.each(GV_LS.CaseFeeTypes, function (i, f) {
                var node = {};
                node.id = f.FeeTypeId;
                node.pId = f.TypeId;
                node.name = f.FeeTypeName;
                node.open = false;
                zNodes.push(node);
            });

            $.fn.zTree.init($("#caseFeeTypeTree"), setting, zNodes);

            return;
        },
        zTreeOnClick: function (event, treeId, treeNode) {
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
        zTreeOnClick: function(event, treeId, treeNode) {
        },
        getAllCasePhaseListTreeHtml: function () {
            var setting = {
                view: {
                    showLine: false,
                },
                check: {
                    enable: true,
                    chkStyle: "checkbox",
                    radioType: "all"
                },

                callback: {
                    onClick: $.lsCasePhase.zTreeOnClick,
                },
                data: {
                    simpleData: {
                        enable: true
                    }
                }
            };

            var zNodes = [];

            $.each(GV_LS.CaseTypes, function (i, c) {
                if (c.CaseTypeId != 140) {
                    var node = {};
                    node.id = c.CaseTypeId;
                    node.pId = c.CaseTypeId;
                    node.name = c.CaseTypeName;
                    node.open = c.CaseTypeId == 110 ? true : false;
                    zNodes.push(node);

                    $.each(GV_LS.CasePhaseTypes, function (j, f) {

                        if (f.CaseTypeId == c.CaseTypeId) {
                            var node = {};
                            node.id = f.CasePhaseId;
                            node.pId = f.ParentPhaseId == f.CasePhaseId ? f.CaseTypeId : f.ParentPhaseId;
                            node.name = f.CasePhaseName;
                            node.open = false;
                            zNodes.push(node);
                        }
                    });
                }
            });
            $.fn.zTree.init($("#casePhaseTree"), setting, zNodes);
            //var zTree = $.fn.zTree.getZTreeObj("casePhaseTree");
            //$("#selectAll").bind("click", selectAll);
            return;
        },
        getcasePhaseListTreeHtml: function (caseTypeId) {
            var setting = {
                view: {
                    showLine: false,
                },
                check: {
                    enable: true,
                    chkStyle: "checkbox",
                    radioType: "all"
                },

                callback: {
                    onClick: $.lsCasePhase.zTreeOnClick,
                },
                data: {
                    simpleData: {
                        enable: true
                    }
                }
            };

            var zNodes = [];
     
            $.each(GV_LS.CasePhaseTypes, function (j, f) {
                
                if (f.CaseTypeId == caseTypeId) {
                    var node = {};
                    node.id = f.CasePhaseId;
                    node.pId = f.ParentPhaseId;
                    node.name = f.CasePhaseName;
                    node.open = false;
                    zNodes.push(node);
                }
            });
         
            $.fn.zTree.init($("#casePhaseTree"), setting, zNodes);
            //var zTree = $.fn.zTree.getZTreeObj("casePhaseTree");
            //$("#selectAll").bind("click", selectAll);
 
            return ;
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
        getCasePhaseCheckBoxListHtmlGroupByCaseType: function () {
            var html = "<div class='i_common_box' style='display: none; width:750px' id='divCasePhaseCheckBoxList'>"
                + "<input type='hidden' id='hidCasePhaseId'>"
                + "<input type='hidden' id='hidCasePhaseName'>"

            $.each(GV_LS.CaseTypes, function (i, c) {
                if (c.CaseTypeId != 140)
                {
                    html += "<div class='i_common_hd'>" + c.CaseTypeName + "</div>"
                    html += "<div class='i_common_bd'>"
                    html += "<ul class='i_common_ul layoutfix'>";
                    $.each(GV_LS.CasePhaseTypes, function (j, f) {
                        if (c.CaseTypeId == f.CaseTypeId) {
                            html += "<li  style='width:130px'><div><input type='checkbox' casephaseid='" + f.CasePhaseId + "' casephasename='" + f.CasePhaseName + "' /><lable>" + f.CasePhaseName + "</lable></div></li>";
                        }
                    });
                    html += "</ul></div>"
                }
            });

            //$.each(GV_LS.CasePhaseTypes, function (j, f) {
            //    html += "<li  style='width:180px'><div><input type='checkbox' casephaseid='" + f.CasePhaseId + "' casephasename='" + f.CasePhaseName + "' /><lable>" + f.CasePhaseName + "</lable></div></li>";
            //});

            html += "</div>"

            return html;
        },
        getCasePhaseCheckBoxListHtmlByCaseTypeId: function (caseTypeId) {
            var html = "<div class='i_common_box' style='display: none; width:750px' id='divCasePhaseCheckBoxList'>"
                + "<div class='i_common_hd'>从下列案件阶段中选择"
                + "<input type='hidden' id='hidCasePhaseId'>"
                + "<input type='hidden' id='hidCasePhaseName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_LS.CasePhaseTypes, function (j, f) {
                if (f.CaseTypeId == caseTypeId) {
                    html += "<li  style='width:180px'><div><input type='checkbox' casephaseid='" + f.CasePhaseId + "' casephasename='" + f.CasePhaseName + "' /><lable>" + f.CasePhaseName + "</lable></div></li>";
                }
            });

            html += "</ul>"
                + " </div>"
                + "</div>";
            return html;
        },
        getSubCasePhases: function (parentPhaseId)
        {
            var subCasePhases = new Array();

            $.each(GV_LS.CasePhaseTypes, function (i, f) {
                if (f.ParentPhaseId == parentPhaseId) {
                    subCasePhases.push(f);
                }
                else if (f.CasePhaseId == parentPhaseId) {
                    subCasePhases.push(f);
                }
            });

            return subCasePhases;
        }
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

    $.lsCaseInfringementWay = {
        getCaseInfringementWayCheckBoxListHtml: function () {
            var html = "<div class='i_common_box' style='display: none;' id='divCaseInfringementWayCheckBoxList'>"
                + "<div class='i_common_hd'>从下列侵权方式中选择"
                + "<input type='hidden' id='hidInfringementWayId'>"
                + "<input type='hidden' id='hidInfringementWayName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            var infringementWays = [];

            infringementWays.push("生产");
            infringementWays.push("销售");
            infringementWays.push("店招");
            infringementWays.push("企业名称");
            infringementWays.push("店内设施");

            $.each(infringementWays, function (j, f) {
                html += "<li><div><input type='checkbox' infringementwayname='" + f + "' /><lable>" + f + "</lable></div></li>";
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
        getCaseTaskTypeListHtml: function (typeId) {

            debugger
            var html = "<div class='i_common_box' style='display: none; width:440px' id='divCaseTaskTypeList'>"
                + "<div class='i_common_hd'>从下列任务类型中选择"
                + "<input type='hidden' id='hidCaseTaskTypeId'>"
                + "<input type='hidden' id='hidCaseTaskTypeName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            if (typeId == null || typeId == '') {
                $.each(GV_LS.CaseTaskTypes, function (j, f) {
                    if (f.BaseTypeId == 1) {
                        html += "<li style='width:125px'><a href='javascript:void(0)' caseTaskTypeId=" + f.TaskTypeId + " skipDays=" + f.SkipDays + " gapDays=" + f.GapDays + " officer=" + f.Officer + " caseTaskTypeName='" + f.TaskTypeName + "'>" + f.TaskTypeName + "</a></li>";
                    }
                });
            }
            else {
                $.each(GV_LS.CaseTaskTypes, function (j, f) {
                    if (f.CaseTypeId == typeId && f.BaseTypeId == 1) {
                        html += "<li style='width:125px'><a href='javascript:void(0)' caseTaskTypeId=" + f.TaskTypeId + " skipDays=" + f.SkipDays + " gapDays=" + f.GapDays + " officer=" + f.Officer + " caseTaskTypeName='" + f.TaskTypeName + "'>" + f.TaskTypeName + "</a></li>";
                    }
                });
            }

            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
    }

    $.notaryOffice = {
        getNotaryOfficeListHtml: function () {

            var html = "<div class='i_common_box' style='display: none; width:440px' id='divNotaryOfficeList'>"
                + "<div class='i_common_hd'>从下列公证处中选择"
                + "<input type='hidden' id='hidNotaryOfficeId'>"
                + "<input type='hidden' id='hidNotaryOfficeName'>"
                + "<input type='hidden' id='hidNotaryOfficeTemplateName'>"
                + "</div>"
                + "<div class='i_common_bd'>"
                + "<ul class='i_common_ul layoutfix'>";

            $.each(GV_LS.NotaryOffices, function (j, f) {
                html += "<li style='width:125px'><a href='javascript:void(0)' notaryOfficeId=" + f.NotaryOfficeId
                    + " notaryOfficeName='" + f.NotaryOfficeName + "'"
                    + " templateName='" + f.TemplateName + "'>"
                    + f.NotaryOfficeName + "</a></li>";
            });

            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
    }

    $.customer = {
        Init: function () {
            var province = $("#Customer_CustomerBasic_Province").val();
            var city = $("#Customer_CustomerBasic_City").val();
            $('#district').citys({ code: city });
        },
        BindEvent: function () {
            $(document).off('click', '#btnCustomerEdit').on('click', '#btnCustomerEdit', function () {
                $(":input", "#customerForm").each(function () {
                    $(this).removeAttr("disabled", "disabled");
                });

                $("#Customer_CustomerBasic_CustomerNo").attr("disabled", "disabled");
                $("#Customer_CustomerBasic_CustomerName").attr("disabled", "disabled");
                $("#btnCustomerCreateUpdate").css("display", "inline-block")
                $("#btnCustomerEdit").css("display", "none")
            });

            $(document).off('click', '#btnCustomerCreateUpdate').on('click', '#btnCustomerCreateUpdate', function () {
                $.customer.CreateUpdate();
            });



            $(document).off('click', '#btnCustomerCancle,#btnCustomerClose').on('click', '#btnCustomerCancle,#btnCustomerClose', function () {
                $.customer.Close();
            });
        },
        Open: function (callBackFunc) {
            var data = {};
            var url = AP_ROOT + AP_PAGE_ID + "/CRM/Customer/Customer";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#customerModal').modal({ backdrop: 'static', keyboard: false });
                $('#customerModal').on('hidden.bs.modal', function () {
                    $("#customerModal").remove();
                });

                $.customer.Init();
                $.customer.BindEvent();

                $(document).off('click', '#btnCustomerCreate').on('click', '#btnCustomerCreate', function () {

                    $.customer.CreateUpdate(callBackFunc);
                });
            });
        },
        /*查看客户*/
        View: function (customerNo) {
            var data = { customerNo: customerNo };
            var url = AP_ROOT + AP_PAGE_ID + "/CRM/Customer/ViewCustomer";
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);
                $('#customerModal').modal({ backdrop: 'static', keyboard: false });
                $('#customerModal').on('hidden.bs.modal', function () {
                    $("#customerModal").remove();
                });

                $(":input", "#customerForm").each(function () {
                    $(this).attr("disabled", "disabled");
                });

                $.customer.Init();
                $.customer.BindEvent();
            });
        },
        /*关闭客户*/
        Close: function () {
            $('#customerModal').modal('hide');
        },

        CreateUpdate: function (callBackFunc) {

            if ($("#Customer_CustomerBasic_CustomerName").val() == '') {
                $.showModalMessageBox("请输入客户名称.");
                return false;
            }

            if ($("#province").val() != "- 请选择 -") {
                $("#Customer_CustomerBasic_Province").val($("#province").val());
            }

            if ($("#city").val() != "- 请选择 -") {
                $("#Customer_CustomerBasic_City").val($("#city").val());
            }


            var regdaddress = /^.*[\\\'\"<>|]+.*$/;
            if (regdaddress.test($("#Customer_CustomerRegistration_RegistrationAddress").val())) {
                $.showModalMessageBox("注册地址禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }

            var regd = /^.*[-—\\\'\"<>|]+.*$/;
            if (regd.test($("#Customer_CustomerRegistration_LicenseNo").val())) {
                $.showModalMessageBox("统一社会信用代码禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }

            if (regd.test($("#Customer_CustomerBasic_Zip").val())) {
                $.showModalMessageBox("邮编禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
                return false;
            }

            $("#customerForm").ajaxPost(AP_ROOT + AP_PAGE_ID + "/CRM/Customer/CaseCustomerCreateUpdate", function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");

                    if (callBackFunc != null) {
                        callBackFunc(response.Data.CustomerBasic.CustomerId, response.Data.CustomerBasic.CustomerNo, response.Data.CustomerBasic.CustomerName);
                    }

                    $.customer.Close();

                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },

    };

    $.paymentType = {

        BindEvent: function () {

            $(document).off('click', '#btnPaymentTypeCancel,#btnPaymentTypeClose').on('click', '#btnPaymentTypeCancel,#btnPaymentTypeClose', function () {
                $.paymentType.Close();
            });
        },

        Open: function (callBackFunc_Input,callBackFunc) {
            
            var url = AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/PaymentType";
            var data = {
                paymentTypeId: null
            };
            $.openLoading();

            $("<div></div>").load(url, data, function (result) {
                $.closeLoading();
                $(document.body).append(result);

                $('#paymentTypeModal').modal({ backdrop: 'static', keyboard: false });
                $('#paymentTypeModal').on('hidden.bs.modal', function () {
                    $("#paymentTypeModal").remove();
                });

                //$.paymentType.Init();
                $.paymentType.BindEvent();

                $(document).off('click', '#btnPaymentType').on('click', '#btnPaymentType', function () {
                    $.paymentType.CreateUpdate(callBackFunc_Input,callBackFunc);
                });
            });
        },

        View: function (e) {
            
            var organizationname = $(e).attr("organizationname");
            var account = $(e).attr("account");
            var accountbank = $(e).attr("accountbank");

            return '<table class="table table-bordered">' +
                        '<tr><td style="text-align:left;width:30%" >收款单位</td><td style="text-align: left;width:70%">' + organizationname + '</td></tr>' +
                        '<tr><td style="text-align:left;width:30%">账号</td><td style="text-align: left;width:70%">' + account + '</td></tr>' +
                        '<tr><td style="text-align:left;width:30%">银行</td><td style="text-align: left;width:70%">' + accountbank + '</td></tr>' +
                    '</table>';
        },
        /**/
        Close: function () {
            $('#paymentTypeModal').modal('hide');
        },

        CreateUpdate: function (callBackFunc_Input,callBackFunc) {

            if ($("#PaymentType_PaymentTypeName").val() == '') {
                $.showModalMessageBox("请输入类型名称.");
                return false;
            }
            var data = {};

            data["PaymentType.PaymentTypeId"] = $("#PaymentType_PaymentTypeId").val(); 
            data["PaymentType.CaseFeeTypeId"] = $("#PaymentType_CaseFeeTypeId").val();
            data["PaymentType.PaymentTypeName"] = $("#PaymentType_CaseFeeTypeId").text();
            data["PaymentType.OrganizationName"] = $("#PaymentType_OrganizationName").val();
            data["PaymentType.AccountBank"] = $("#PaymentType_AccountBank").val();
            data["PaymentType.Account"] = $("#PaymentType_Account").val();
            
            $.ajaxPost(AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/PaymentTypeCreateUpdate", data, function (response) {
                if (response.IsSuccess) {
                    $.showModalMessageBox("保存成功.");
                    $.paymentType.Close();
                    if (callBackFunc)
                    {
                        var target = $(callBackFunc_Input).parent();
                        callBackFunc(target, response.Data.PaymentType,false);
                        $(callBackFunc_Input).val('');
                        $(callBackFunc_Input).focus();
                    }
                }
                else {
                    $.showModalMessageBox(response.Message);
                }
            });

            return true;
        },
    };

    $.court = {

    }

    $.courtOfficer = {
        getcourtOfficerListHtml: function (courtNo) {
            var data = {
                courtNo: courtNo,
            };

            $.ajaxSetup({
                async: false
            });

            var html = "<div class='i_common_box' style='display: none;' id='div_CourtOfficerList'>"
                            + "<div class='i_common_hd'>从下列人员中选择"
                            + "<input type='hidden' id='hidCourtOfficerId'>"
                            + "<input type='hidden' id='hidCourtOfficerName'>"
                            + "</div>"
                            + "<div class='i_common_bd'>"
                            + "<ul class='i_common_ul layoutfix'>";

            $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/BAS/CourtOfficer/GetCourtOfficers", data, function (response) {
                if (response.IsSuccess) {
                    if (response.Data.length > 0) {
                        $.each(response.Data, function (j, f) {
                            html += "<li><a href='javascript:void(0)' id='" + f.Item1 + "'>" + f.Item2 + "</a></li>";
                        });
                    }
                    else {
                        html += "<div>无人员信息.</div>";
                    }
                }
            }, false);

            $.ajaxSetup({
                async: true
            });

            html += "</ul>"
                + " </div>"
                + "</div>";

            return html;
        },
    },

    $.warehouse = {
        type: {
            warehouse: "warehouse",
            location: "location",
        },
        getwarehouseListTreeHtml: function () {
            var setting = {
                view: {
                    showLine: false,
                },
                check: {
                    enable: true,
                    chkStyle: "radio",
                    radioType: "all"
                },

                callback: {
                    onClick: function (event, treeId, treeNode) {

                    },
                },
                data: {
                    simpleData: {
                        enable: true
                    }
                }
            };
            var zNodes = [];
            $.ajaxSetup({
                async: false
            });
            var data = {};
            $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/BAS/Warehouse/GetWarehouses", data, function (response) {
                if (response.Data.Warehouses.length > 0) {
                    var zNodes = [];
                    $.each(response.Data.Warehouses, function (i, warehouse) {
                        var node = {};
                        node.id = warehouse.WarehouseNo;
                        node.pId = warehouse.WarehouseNo;
                        node.name = warehouse.WarehouseName;
                        node.open = false;
                        node.typeId = $.warehouse.type.warehouse;
                        zNodes.push(node);

                        if (warehouse.Locations.length > 0) {
                            $.each(warehouse.Locations, function (i, location) {
                                var node = {};
                                node.id = location.StorageLocationNo;
                                node.pId = warehouse.WarehouseNo;
                                node.name = location.StorageLocationName;
                                node.no = location.StorageLocationName;
                                node.open = false;
                                node.typeId = $.warehouse.type.location;
                                zNodes.push(node);
                            });
                        }

                    });
                    $.fn.zTree.init($("#warehouseTree"), setting, zNodes);
                    
                }
            }, false);

            $.ajaxSetup({
                async: true
            });

            //$.fn.zTree.init($("#warehouseTree"), setting, zNodes);
            //var zTree = $.fn.zTree.getZTreeObj("warehouseTree");
            
            return;
        },
    }


})(jQuery);
 
//获取内网ip方式1：
function getIP() {
    let recode = {};
    let RTCPeerConnection = window.RTCPeerConnection || window.mozRTCPeerConnection || window.webkitRTCPeerConnection;
    // 如果不存在则使用一个iframe绕过
    if (!RTCPeerConnection) {
        // 因为这里用到了iframe，所以在调用这个方法的script上必须有一个iframe标签
        // <iframe id="iframe" sandbox="allow-same-origin" style="display:none;"></iframe>
        let win = iframe.contentWindow;
        RTCPeerConnection = win.RTCPeerConnection || win.mozRTCPeerConnection || win.webkitRTCPeerConnection;
    }

    //创建实例，生成连接
    let pc = new RTCPeerConnection();

    // 匹配字符串中符合ip地址的字段
    function handleCandidate(candidate) {
        let ip_regexp = /([0-9]{1,3}(\.[0-9]{1,3}){3}|([a-f0-9]{1,4}((:[a-f0-9]{1,4}){7}|:+[a-f0-9]{1,4}){6}))/;
        let ip_isMatch = candidate.match(ip_regexp)[1];
        console.log("---ip(内)---" + ip_isMatch);
        if (!recode[ip_isMatch]) {
            recode[ip_isMatch] = true;
        }
    }

    //监听icecandidate事件
    pc.onicecandidate = (ice) => {
        if (ice.candidate) {
            handleCandidate(ice.candidate.candidate);
        }
    };
    //建立一个伪数据的通道
    pc.createDataChannel('');
    pc.createOffer((res) => {
        pc.setLocalDescription(res);
    }, () => { });

    //延迟，让一切都能完成
    setTimeout(() => {
        let lines = pc.localDescription.sdp.split('\n');
        lines.forEach(item => {
            if (item.indexOf('a=candidate:') === 0) {
                handleCandidate(item);
            }
        })
    }, 1000);
}

var messager = {
    polling: function (show) {
        var data = {}
        var taskListUrl = AP_ROOT + "9001001100/TP/Task/TaskList";
        var taskUrl = AP_ROOT + "9001001100/TP/Task/TaskList?taskId=";
        $.ajaxPostMessage(AP_ROOT + "9001001100/TP/Task/GetTaskNotificationMessages", data, function (response) {
            if (response.IsSuccess) {
                if (response.Data.TaskNotificationMessages.length > 0) {
                    if (show) {
                        $.messager.lays(320, 120);
                        $.messager.show('任务新消息',
                            '您目前尚有<font color=red>' + response.Data.TaskNotificationMessages.length + '</font>个消息未查看，请尽快查看！ <a style="color: #06C;" href=' + taskListUrl + '  target=_self>进入查看</a>',
                            10000);
                    }

                    $("#taskNotificationMessagesNum").html(response.Data.TaskNotificationMessages.length);

                    $("ul", "#taskNotificationMessagesBody").html('');

                    var html = '';
                    $.each(response.Data.TaskNotificationMessages, function (i, m) {

                        var url = taskUrl + m.TaskId;
                        html += "<li  class='ng-scope'><a target='_self' class='clearfix' onclick='task.Tasks.Task.View(" + m.TaskId + ");' >"
                        html += "<span class='inline-block'><span class='topbar-notice-link ng-binding' ng-ind='item.title'>" + m.CaseNo + "_" + m.TaskTitle + "_" + m.Content;
                        html += "</span><span class='topbar-notice-time ng-binding'>" + getDate(convertJsonDateToJSDate(m.TaskEndTime))
                        html += "</span></span><span class='inline-block topbar-notice-class ng-scope' ><span class='topbar-notice-class-name ng-binding'>" + "案件任务" + "</span></span></a></li>";

                    });

                    $("ul", "#taskNotificationMessagesBody").html(html);

                } else {
                    $("#taskNotificationMessagesNum").html('0');
                }
            }
        }, false);

        //var taskListUrl = AP_ROOT + "9001001100/TP/Task/TaskList";
        //var taskUrl = AP_ROOT + "9001001100/TP/Task/TaskList?taskId=";
        $.ajaxPostMessage(AP_ROOT + "2001002/Account/MessageCenter/GetUnReadMessages", data, function (response) {
            if (response.IsSuccess) {
                if (response.Data.Messages.length > 0) {
        
                    $("#notificationMessagesNum").html(response.Data.Messages.length);
                    $(".total-unread-count").html(response.Data.Messages.length);

                    $("ul", "#notificationMessagesBody").html('');

                    var html = '';
                    $.each(response.Data.Messages, function (i, m) {

                        //var url = taskUrl + m.MessageId;
                        html += "<li  class='ng-scope'><a target='_self' class='clearfix' onclick='javascript:message.Open(" +  m.MessageId + ")' href='javascript:void(0);'>"
                        html += "<span class='inline-block'><span class='topbar-notice-link ng-binding' ng-ind='item.title'>" + m.Title + "_" + m.Content;
                        html += "</span><span class='topbar-notice-time ng-binding'>" + getDate(convertJsonDateToJSDate(m.SendTime))
                        html += "</span></span><span class='inline-block topbar-notice-class ng-scope' ><span class='topbar-notice-class-name ng-binding'>" + "未读消息" + "</span></span></a></li>";

                    });

                    $("ul", "#notificationMessagesBody").html(html);

                } else {
                    $(".total-unread-count").html('0');
                    $("#notificationMessagesNum").html('0');
                    $("#notificationMessagesBody").html('');
                }
            }
        }, false);

    }
}

var payment = {
    PaymentTypeId: {
        OfficeFee: 1,
        NonOfficeFee: 2,
        CommissionFee: 3
    },
}

function addtabs(url, title, icon) {
    var dom = "a[url='{url}']"
    var leftlink = top.window.$(dom.replace(/\{url\}/, url));
    if (leftlink.length > 0) {
        leftlink.trigger("click");
    } else {
        //url = Fast.api.fixurl(url);
        leftlink = top.window.$(dom.replace(/\{url\}/, url));
        if (leftlink.length > 0) {
            var event = leftlink.parent().hasClass("active") ? "dblclick" : "click";
            leftlink.trigger(event);
        } else {
            var baseurl = url.substr(0, url.indexOf("?") > -1 ? url.indexOf("?") : url.length);
            leftlink = top.window.$(dom.replace(/\{url\}/, baseurl));
            //能找到相对地址
            if (leftlink.length > 0) {
                icon = typeof icon != 'undefined' ? icon : leftlink.find("i").attr("class");
                title = typeof title != 'undefined' ? title : leftlink.find("span:first").text();
                leftlink.trigger("fa.event.toggleitem");
            }
            var navnode = $(".nav-tabs ul li a[node-url='" + url + "']");
            if (navnode.length > 0) {
                navnode.trigger("click");
            } else {
                //追加新的tab
                var id = Math.floor(new Date().valueOf() * Math.random());
                icon = typeof icon != 'undefined' ? icon : 'fa fa-circle-o';
                title = typeof title != 'undefined' ? title : '';
                localStorage.setItem("lastpagetitle", title);

                top.window.$("<a />").append('<i class="' + icon + '"></i> <span>' + title + '</span>').prop("href", url).attr({ url: url, addtabs: id }).addClass("hide").appendTo(top.window.document.body).trigger("click");
            }
        }
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

        $.each(GV_LS.CaseFileTypes, function (i, f) {
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

function AssociateTaskType(div, ctlid, ctlname, caseTypeId, func) {

    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.TaskType = function () {
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }
        var curobj = new Object();
        curobj.keyword = name;

        var html = '';

        $.each(GV_LS.CaseTaskTypes, function (i, f) {
            if (f.CaseTypeId == caseTypeId) {
                if (f.TaskTypeId.toString().indexOf(name) > -1 || f.TaskTypeName.toString().indexOf(name) > -1) {
                    html += '<a href="javascript:void(0)" taskTypeId=' + f.TaskTypeId + '>' + f.TaskTypeName + '</a>';
                }
            }
        });

        $(div).find(".i_common_list").html(html);
        $(div).find(".i_common_list a").click(function () {
            $(ctlid).val($(this).attr("fileTypeId"));
            $(ctlname).val($(this).text());
            var caseFileTypeId = $(this).attr("fileTypeId");
            var caseFileTypeNameText = $(this).text();
         
            $(div).hide();
        });

         
        $(div).css({
            "position": "absolute",
            "left": $(ctlname).position().left + 2,
            "top": $(ctlname).position().top + 26,
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
            event.data.obj.Event = setTimeout(function () { event.data.obj.TaskType(event.data.obj); }, 500);
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
                    "left": $(ctlname).parent().position().left + 0,
                    "top": $(ctlname).parent().position().top + 26,
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

function AssociatePaymentType(div, ctlid, ctlname, func,add_func) {
    
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;
    this.CallBackFunc = func;

    this.SearchKeyword = function () {
        
        var keyword = ctlname.val();
        if ($.trim(keyword) == "") {
            return false;
        }
        var curobj = new Object();
        curobj.keyword = keyword;

        var html = '';
        
        var data = { keyword: keyword };
        $.ajaxPostMessage(AP_ROOT + AP_PAGE_ID + "/System/SystemCenter/GetPaymentTypeList", data, function (response) {
            if (response.IsSuccess) {
                
                $.each(response.Data.PaymentTypeList, function (i, t) {
                    html += '<a name="paymentype" href="javascript:void(0)" paymentTypeId=' + t.PaymentTypeId
                        + ' organizationName=' + t.OrganizationName
                        + ' account=' + t.Account
                        + ' accountBank=' + t.AccountBank
                        + ' remark=' + t.Remark
                        + '>' + t.Account + "_" + t.OrganizationName + "_" + t.AccountBank + '</a>';
                });

                html += '<a href="javascript:void(0)"   onclick="javascript:$.paymentType.Open(' + $(ctlname).attr("id") + ',' + add_func + ');">新增收款单位</a>';

                $(div).find(".i_common_list").html(html);
                $(div).find(".i_common_list a[name='paymentype']").click(function () {

                    if (func != null) {
                        var target = $(ctlid).parent();
                        var paymentType = {
                            PaymentTypeId: $(this).attr("paymentTypeId"),
                            OrganizationName: $(this).attr("organizationName"),
                            Account: $(this).attr("account"),
                            AccountBank: $(this).attr("accountBank"),
                            Remark: $(this).attr("remark")
                        };
                        func(target, paymentType,false);
                        $(ctlname).val('');
                        $(ctlname).focus();
                    }
                    else {
                        $(ctlid).val($(this).attr("paymentTypeId"));
                        $(ctlname).val($(this).text());
                    }
                    $(div).hide();
                });
                
                $(div).css({
                    "position": "absolute",
                    "height": $(ctlname).outerHeight() - 32,
                    "line-height": ($(ctlname).outerHeight() - 4) + "px",
                    "width": "450px",
                    "top": $(ctlname).offset().top - 65 ,
                    "left": $(ctlname).position().left + 55,
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
            event.data.obj.Event = setTimeout(function () { event.data.obj.SearchKeyword(event.data.obj); }, 500);
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

    $(function () {
        var inputs = $("input[type='text'],select,button,textarea");
        inputs.keydown(function (e) {
            var k = e.keyCode;
            var a = inputs.index($(this));//jquery 获取数组元素的下标,两种方法
            if (k == 13 || k == 39) {
                
                if (e.target.id == "txtKeyword") {
                    jQuery("#btnSearchGo").click();
                }
                else {
                    inputs[a + 1].focus();
                    return false;
                }
            } else if (k == 37) {
                inputs[a - 1].focus();
            }
        })
    })

    //$(document).off('click', '#txtKeyword').on('keydown', '#txtKeyword', function () {
    //    
    //    if (event.keyCode == 13) {
    //        var k = $("#txtKeyword").val().trim();
    //        if (k == '') {
    //            return false;
    //        }
    //        var regd = /^.*[\\\'\"<>|-—]+.*$/;
    //        if (regd.test(k)) {
    //            $.showModalMessageBox("禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
    //            return false;
    //        }
    //        var url = AP_ROOT + "1001001001/Legal/CaseList/List?k=" + escape(k);
    //        window.location = url;
    //    }
    //});

    $(function () { $("[data-toggle='tooltip']").tooltip(); });

    if ($("li.nav-item.ng-scope.active").length) {

        var linvaid = $("li.nav-item.ng-scope.active").attr("li-nva-id");
        var trigger = $("li.nav-item.ng-scope.active").parents().find(".sidebar-nav")[linvaid];

        //setsidebarnav(trigger);

        //jQuery(trigger).click();
    }

    //messager.polling(false);
    //setInterval("messager.polling(true)", 6000*5);//半分钟刷新1次

    //$(window).keydown(function (e) {
    //    if (e.which == 13) {
    //        jQuery("#btnSearchGo").click();
    //    }
    //});

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

    $(document).off('click', '#ace-dropdown-toggle').on('click', '#ace-dropdown-toggle', function () {
        setacesidebarnav(this.parentElement);
    });

    $(document).off('click', '#sidebar-collapse').on('click', '#sidebar-collapse', function () {
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
        debugger
        var k = $("#txtKeyword").val().trim();
        if (k == '') {
            return false;
        }
        var regd = /^.*[\\\'\"<>|-—]+.*$/;
        if (regd.test(k)) {
            $.showModalMessageBox("禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
            return false;
        }
        var url = AP_ROOT + "1001001001/Legal/CaseList/List?k=" + escape(k);
        window.location = url;
    });

    //$(document).off('click', '#btnSearchGo').on('click', '#btnSearchGo', function () {
 
    //    debugger
    //    var k = $("#txtKeyword").val().trim();
    //    if (k == '') {
    //        return false;
    //    }
    //    var regd = /^.*[\\\'\"<>|-—]+.*$/;
    //    if (regd.test(k)) {
    //        $.showModalMessageBox("禁止输入 <  >  \"   \'  \\ 半角字符，请检查");
    //        return false;
    //    }
    //    var url = AP_ROOT + "1001001001/Legal/CaseList/List?k=" + escape(k);
    //    window.location = url;
    //});

    $(document).off('click', '.viewFramework-product-navbar-collapse').on('click', '.viewFramework-product-navbar-collapse', function () {
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

    $(document).off('click', '.viewFramework-product-navbar-collapse-3').on('click', '.viewFramework-product-navbar-collapse-3', function () {
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

    $(document).off('click', '.bootstrap-tagsinput').on('click', '.bootstrap-tagsinput', function () {
        $(":input", this).focus();
    });
});

 