$(document).ready(function () {
    $(document).click(function () {
        $("#divCaseFileTypeList").off().hide();
    });

    $("#casefile").fileinput({
        fileType: "any",
        language: 'zh',
        showPreview: true,
        minImageWidth: 50, //图片的最小宽度
        minImageHeight: 50,//图片的最小高度
        maxImageWidth: 100,//图片的最大宽度
        maxImageHeight: 100,//图片的最大高度
        showUploadedThumbs : false,
        uploadUrl: AP_ROOT + AP_PAGE_ID + "/Legal/CaseFile/MultiCaseFileWebUpload",
        uploadExtraData: function () {//向后台传递参数

            //一个案件中上传
            if ($("#CaseFileTypeId").val().length > 0) {
                var data = {
                    caseNos: $("#CaseNos").val(),
                    caseFileTypeId: $("#CaseFileTypeId").val(),
                    uploadingTime: $("#UploadingTime").val(),
                };

                return data;
            }
            else {
                //多个案件上传
                var treeObj = $.fn.zTree.getZTreeObj("caseFileTypeTree");
                var nodes = treeObj.getCheckedNodes(true);
                var data = {
                    caseNos: $("#CaseNos").val(),
                    typeId: nodes[0].typeId,
                    uploadingTime: $("#UploadingTime").val(),
                };
                return data;
            }
        },
    }).on('filebatchpreupload', function (event, data) { //该方法将在上传之前触发

        if ($("#CaseFileTypeId").val().length > 0) return;

        var treeObj = $.fn.zTree.getZTreeObj("caseFileTypeTree");
        var nodes = treeObj.getCheckedNodes(true);
        if (nodes.length < 1) {
            return {
                message: "请选择文档目录",
                data: {} 
            };
        }
    });

    var caseFileType = new AssociateCaseFileType(
        $("#div_CaseFileTypeList"),
        $("#CaseFileTypeId"),
        $("#CaseFileTypeName"),
        $("#SearchCondition_CaseTypeId").val(),
        $("#IsTransformedFile").val() == 'true',
       null
    );

    $(document).off('click', '#divCaseFileTypeList ul li').on('click', '#divCaseFileTypeList ul li', function (i, e) {
        var caseFileTypeId = $(this).find("a").attr("id");
        var caseFileTypeName = $(this).find("a").text();
        var caseFileTypeNameText = $(this).find("a").attr("text");
        var currentSelectedControl = $("#hidCaseFileTypeName").val();
        var currentSelectedIdControl = $("#hidCaseFileTypeId").val();
        $("#" + currentSelectedControl).val(caseFileTypeName);
        $("#" + currentSelectedIdControl).val(caseFileTypeId);

        var hedgingFileTypeId = $(this).find("a").attr("hedgingFileTypeId");
        var hedgingFeeTypeId = $(this).find("a").attr("hedgingFeeTypeId");

        //caseInfo.CaseFile.ProcessFileTypeSelectedCallBack(caseFileTypeId, caseFileTypeNameText, hedgingFileTypeId, hedgingFeeTypeId);

        $("#divCaseFileTypeList").hide();

        return true;
    });

    $(document).off('click', '#lnkCaseOfficeFileTypeId').on('click', '#lnkCaseOfficeFileTypeId', function (e) {
        var tirgger = $("#CaseFileTypeName");

        $(".divCaseFileTypeList").html($.lsCaseFileType.getCaseOfficeFileTypeListHtml($("#SearchCondition_CaseTypeId").val()));

        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left - 100,
            "top": $(tirgger).offsetParent().position().top + 32
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

        return false;
    });

    $(document).off('click', '#lnkCaseNonOfficeFileTypeId').on('click', '#lnkCaseNonOfficeFileTypeId', function (e) {
        var tirgger = $("#CaseFileTypeName");

        $(".divCaseFileTypeList").html($.lsCaseFileType.getCaseNonOfficeFileTypeListHtml($("#SearchCondition_CaseTypeId").val()));

        $("#divCaseFileTypeList").css({
            "position": "absolute",
            "left": $(tirgger).offsetParent().position().left - 100,
            "top": $(tirgger).offsetParent().position().top + 32
        }).toggle();

        $("#hidCaseFileTypeName").val($(tirgger).attr("id")); //名称
        $("#hidCaseFileTypeId").val($("#CaseFileTypeId").attr("id")); //Id

        return false;
    });

});