var ar = {
    List: function () {
        $("#postForm").ajaxPost(AP_ROOT + "FAM/AR/List", function (response) {
            if (response.IsSuccess) {
                $("tbody", "#tblARList").clearRow();
                if (response.Data.TotalItemCount > 0) {
                    $(".info_inall.layoutfix").show();

                    $("tbody", "#tblARList").addRow(
                        '',
                        '',
                        "<span style='font-weight:bold'>" + response.Data.TotalAmount + "</span>",
                        "<span style='font-weight:bold'>" + response.Data.TotalCashedAmount + "</span>",
                        "<span style='font-weight:bold'>" + response.Data.TotalARAmount + "</span>",
                        "<span style='font-weight:bold'>" + response.Data.TotalAROfficeAmount + "</span>",
                        "<span style='font-weight:bold'>" + response.Data.TotalARNoOfficeAmount + "</span>",
                        '',
                        '',
                        '',
                        '',
                        ''
                    );
                    $.each(response.Data.ContractList, function (i, c) {
                        var contractFileId = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileId;
                        var contractFileName = c.DefalutContractFile == null ? '' : c.DefalutContractFile.FileName;

                        $("tbody", "#tblARList").addRow(
                            "<a href='javascript:void(0)' onclick='javascript:ar.Detail(\"" + c.ContractBasicInfo.ContractNo + "\")'>" + c.ContractBasicInfo.ContractNo + "</a> &nbsp;",
                            "<span style='width: 180px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.CustomerName + "</span>",
                            //c.ContractBasicInfo.ContractStatusName,
                            c.ContractBasicInfo.TotalAmount,
                            c.ContractBasicInfo.CashedAmount,
                            c.ContractBasicInfo.ARAmount,
                            c.ContractBasicInfo.ARCaseOfficeFeeAmount,
                            c.ContractBasicInfo.ARCaseNonOfficeFeeAmount,
                            c.ContractBasicInfo.BusinessOwnerName,
                            c.ContractBasicInfo.AuditDate == null ? '' : getDate(convertJsonDateToJSDate(c.ContractBasicInfo.AuditDate)),
                            //"<span style='width: 200px; float: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '>" + c.ContractBasicInfo.ContractName + "</span>",
                           "<a href='javascript:void(0)' onclick='javascript:ar.ContractFile.View(\"" + contractFileId + "\",\"" + c.ContractBasicInfo.ContractNo + "\",\"" + contractFileName + "\")'>合同附件</a> &nbsp;",
                            "<a href='javascript:void(0)' onclick='javascript:ar.GL.View(" + c.ContractBasicInfo.ContractId + ")'>合同台账</a> &nbsp; "
                        );
                    });

                    $("tfoot", "#tblARList").show();
                    $(".simple-grid-none-data-wrap").hide();

                    $(".pull-right.page-box.ARList").cPaging({
                        totalCount: response.Data.TotalItemCount,
                        pageNo: response.Data.PageNo,
                        pageSize: response.Data.PageSize,
                        callBack: ar.List,
                        callBackArgs: null
                    });
                } else {

                    $("tfoot", "#tblARList").hide();
                    $(".simple-grid-none-data-wrap").show();
                }
            }
        });
    },

    Detail: function (contractNo) {
        window.open(AP_ROOT + "FAM/AR/Details?contractNo=" + contractNo);
    },
    /*合同文件*/
    ContractFile: {
 
        /*查看*/
        View: function (contractFileId, contractNo, contractFileName) {

            if (contractFileId == '' || contractFileName == '') {
                $.showModalMessageBox("无合同文件.");
                return false;
            }

            var officefiles = new Array('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt');
            var picfiles = new Array('jpg', 'tif', 'pdf');
            var extName = contractFileName.substring(contractFileName.lastIndexOf('.') + 1, contractFileName.length);

            if ($.inArray(extName.toLowerCase(), officefiles) > -1) {
                var path = GV_IPR.OfficeOnlineUrl + GV_IPR.OnlineUrl + "ContractFiles/" + contractNo + "/" + contractFileName;
                window.open(path);
            }
            else if ($.inArray(extName.toLowerCase(), picfiles) > -1) {
                var path = GV_IPR.OnlineUrl + "ContractFiles/" + contractNo + "/" + contractFileName;
                window.open(path);
            } else {
                contract.ContractFile.Download(contractFileId);
            }

            return true;
        },

        Download: function (contractFileId) {
            window.open(AP_ROOT + "FCM/ContractFile/ContractFileDownload?contractFileId=" + contractFileId);
            return true;
        },
    },

    /*合同台账*/
    GL: {

        /*查看*/
        View: function (contractId) {
            window.open(AP_ROOT + "FCM/GL/index?contractId=" + contractId);
        },
 
    },
};
 
$(document).ready(function () {
    $("#btnSearch").die().live("click", function () {
        ar.List();
    });
});