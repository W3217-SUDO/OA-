$(document).ready(function () {
    staff.Init();
    staff.ResetSize();
    staff.Staff.OffWorkDay.List(false);
});

$(document).off('click', '#btnStaffPerformanceList').on('click', '#btnStaffPerformanceList', function () {
    $("#liStaffOffWorkDayList").removeClass("active");
    $("#liStaffFileList").removeClass("active");
    $("#liStaffEventList").removeClass("active");
    $("#liStaffPerformanceList").removeClass("active");

    $("#liStaffPerformanceList").addClass("active");
    $("#dv_List").css('display', 'block');
    staff.ResetSize();
    staff.Staff.Performance.List(false);
});

$(document).off('click', '#btnStaffOffWorkDayList').on('click', '#btnStaffOffWorkDayList', function () {
    $("#liStaffOffWorkDayList").removeClass("active");
    $("#liStaffFileList").removeClass("active");
    $("#liStaffEventList").removeClass("active");
    $("#liStaffPerformanceList").removeClass("active");

    $("#liStaffOffWorkDayList").addClass("active");
    $("#dv_List").css('display', 'block');
    staff.ResetSize();
    staff.Staff.OffWorkDay.List(false);
});
 
$(document).off('click', '#btnStaffFileList').on('click', '#btnStaffFileList', function () {
    $("#liStaffOffWorkDayList").removeClass("active");
    $("#liStaffFileList").removeClass("active");
    $("#liStaffEventList").removeClass("active");
    $("#liStaffPerformanceList").removeClass("active");

    $("#liStaffFileList").addClass("active");
    $("#dv_List").css('display', 'block');

    staff.Staff.Files.Layout();
});
 
$(document).off('click', '#btnStaffEventList').on('click', '#btnStaffEventList', function () {
    $("#liStaffOffWorkDayList").removeClass("active");
    $("#liStaffFileList").removeClass("active");
    $("#liStaffEventList").removeClass("active");
    $("#liStaffPerformanceList").removeClass("active");

    $("#liStaffEventList").addClass("active");
    $("#dv_List").css('display', 'block');

    staff.Staff.Events.Layout();
});


$(document).off('click', '#flStaffFile').on('click', '#flStaffFile', function () {
    $("#txtStaffFilePath").val($("#flStaffFile").val());
});

$(document).off('click', '#btnStaffFileUpload').on('click', '#btnStaffFileUpload', function () {
    staff.Staff.Files.File.Upload();
});

$(document).off('click', '.btn_stafffile_add').on('click', '.btn_stafffile_add', function () {
    staff.Staff.Files.File.Open();
});

$(document).off('click', '.btn_stafffile_remove').on('click', '.btn_stafffile_remove', function () {
 });

$(document).off('click', '#btnStaffFileCreate').on('click', '#btnStaffFileCreate', function () {
    staff.Staff.Files.File.Open();
});

$(document).off('click', '.btn_staffoffworkday_add').on('click', '.btn_staffoffworkday_add', function () {
    staff.Staff.OffWorkDay.Open(this);
});

$(document).off('click', '.btn_staffevent_add').on('click', '.btn_staffevent_add', function () {
    staff.Staff.Events.Event.Open(this);
});

$(document).off('click', '.btn_staffoffworkday_remove').on('click', '.btn_staffoffworkday_remove', function () {
    var seqId = $(this).attr("seqId");
    staff.Staff.OffWorkDay.Delete(seqId);
});

$(document).off('click', '#btnStaffCreateUpdate').on('click', '#btnStaffCreateUpdate', function () {
    staff.Staff.CreateUpdate(true);
});
 
$(document).off('click', '#btnStaffEvent').on('click', '#btnStaffEvent', function () {
    staff.Staff.Events.Event.Create(true);
});

$(document).off('click', '#btnStaffEventCreate').on('click', '#btnStaffEventCreate', function () {
    staff.Staff.Events.Event.Open(this);
});

$(document).off('click', '#btnStaffFileUploadCancel,#btnStaffFileUploadClose').on('click', '#btnStaffFileUploadCancel,#btnStaffFileUploadClose', function () {
    staff.Staff.Files.File.Close();
});

$(document).off('click', '#btnStaffEventCancel,#btnStaffEventClose').on('click', '#btnStaffEventCancel,#btnStaffEventClose', function () {
    staff.Staff.Events.Event.Close();
});

$(document).off('click', '#btnPerformanceCancel,#btnPerformanceClose').on('click', '#btnPerformanceCancel,#btnPerformanceClose', function () {
    staff.Staff.Performance.Close();
});
