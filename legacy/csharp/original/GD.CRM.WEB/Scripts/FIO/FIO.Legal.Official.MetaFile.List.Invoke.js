$(document).ready(function() {
    officialFile.MetaFile.List();
    officialFile.ResetSize();
    $(window).resize(function () {
        officialFile.ResetSize();
    })

    $(document).off('click', '#btnMetaFileSearch').on('click', '#btnMetaFileSearch', function () {
        officialFile.MetaFile.List();
    });

    $(document).off('click', '#btnFileUpload').on('click', '#btnFileUpload', function () {
        officialFile.MetaFile.Open();
    });

    $(document).off('click', '#chkMetaFileAll').on('click', '#chkMetaFileAll', function () {
        officialFile.MetaFile.SelectedAll(this);
    });

    $(document).off('click', '#btnMetaFileDelete').on('click', '#btnMetaFileDelete', function () {
        var metaFileIds = $.checkbox.vals("chkMetaFileId");
        if (metaFileIds.length == 0) {
            $.showModalMessageBox("请选择文件.");
            return false;
        }
        officialFile.MetaFile.Delete(metaFileIds);
    });

    $(document).off('click', '#flMetaFile').on('change', '#flMetaFile', function (e) {
        $("#flMetaFilePath").val($("#flMetaFile").val());
    });

    $(document).off('click', '#btnMetaFileInformDateChanged').on('click', '#btnMetaFileInformDateChanged', function () {
        if ($("#MetaFile_InformDate").val() == '') {
            $.showTips('请输入收文日期.', 0, 3);
            return false;
        }
        var metaFileIds = $("#MetaFileIds").val();
        var informDate = $("#MetaFile_InformDate").val();
        officialFile.MetaFile.InformDate.Change(metaFileIds, informDate, officialFile.MetaFile.List);
    });

    $(document).off('click', '#btnInformDateChange').on('click', '#btnInformDateChange', function () {
        if ($.checkbox.vals('chkMetaFileId').length == 0) {
            $.showTips('请选择案件.', 0, 3);
            return false;
        }
        var metaFileIds = [];
        $("input[name=chkMetaFileId]:checked").each(
            function () {
                metaFileIds.push($(this).val());
            }
        );
        officialFile.MetaFile.InformDate.Open(metaFileIds);
    });
});