$(document).ready(function () {

    $(document).click(function () {
        $("#div_CourtOfficerList").off().hide();
        $(".divfirstCourtJudgeList").empty();
        $(".divfirstCourtClerkList").empty();
        $(".divsecondCourtJudgeList").empty();
        $(".divsecondCourtClerkList").empty();
        $(".divexecutionCourtJudgeList").empty();
        $(".divexecutionCourtClerkList").empty();
        $(".divlastCourtJudgeList").empty();
        $(".divlastCourtClerkList").empty();
     });

    $(document).off('click', '#Case_Basic_FirstIntanceJudgeName').on('click', '#Case_Basic_FirstIntanceJudgeName', function () {
        
        var tirgger = this;
        var html = $.courtOfficer.getcourtOfficerListHtml($("#Case_Basic_FirstIntanceCourt").val());
        
        $(".divfirstCourtJudgeList").html(html);
        $("#hidCourtOfficerId").val("Case_Basic_FirstIntanceJudge");
        $("#hidCourtOfficerName").val("Case_Basic_FirstIntanceJudgeName");

        $("#div_CourtOfficerList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 0,
            "top": $(tirgger).parent().position().top + 26,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#Case_Basic_FirstIntanceClerkName').on('click', '#Case_Basic_FirstIntanceClerkName', function () {
        var tirgger = this;
      
        var html = $.courtOfficer.getcourtOfficerListHtml($("#Case_Basic_FirstIntanceCourt").val());
        $(".divfirstCourtClerkList").html(html);
        $("#hidCourtOfficerId").val("Case_Basic_FirstIntanceClerk");
        $("#hidCourtOfficerName").val("Case_Basic_FirstIntanceClerkName");

        $("#div_CourtOfficerList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 0,
            "top": $(tirgger).parent().position().top + 26,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#Case_Basic_SecondIntanceJudgeName').on('click', '#Case_Basic_SecondIntanceJudgeName', function () {
        var tirgger = this;
        var html = $.courtOfficer.getcourtOfficerListHtml($("#Case_Basic_SecondIntanceCourt").val());
        $(".divsecondCourtJudgeList").html(html);
        $("#hidCourtOfficerId").val("Case_Basic_SecondIntanceJudge");
        $("#hidCourtOfficerName").val("Case_Basic_SecondIntanceJudgeName");

        $("#div_CourtOfficerList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 0,
            "top": $(tirgger).parent().position().top + 26,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#Case_Basic_SecondIntanceClerkName').on('click', '#Case_Basic_SecondIntanceClerkName', function () {
        var tirgger = this;
        var html = $.courtOfficer.getcourtOfficerListHtml($("#Case_Basic_SecondIntanceCourt").val());
        $(".divsecondCourtClerkList").html(html);
        $("#hidCourtOfficerId").val("Case_Basic_SecondIntanceClerk");
        $("#hidCourtOfficerName").val("Case_Basic_SecondIntanceClerkName");

        $("#div_CourtOfficerList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 0,
            "top": $(tirgger).parent().position().top + 26,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#Case_Basic_ExecutionIntanceJudgeName').on('click', '#Case_Basic_ExecutionIntanceJudgeName', function () {
        var tirgger = this;
        var html = $.courtOfficer.getcourtOfficerListHtml($("#Case_Basic_ExecutionIntanceCourt").val());
        $(".divexecutionCourtJudgeList").html(html);
        $("#hidCourtOfficerId").val("Case_Basic_ExecutionIntanceJudge");
        $("#hidCourtOfficerName").val("Case_Basic_ExecutionIntanceJudgeName");

        $("#div_CourtOfficerList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 0,
            "top": $(tirgger).parent().position().top + 26,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#Case_Basic_ExecutionIntanceClerkName').on('click', '#Case_Basic_ExecutionIntanceClerkName', function () {
        
        var tirgger = this;
        var html = $.courtOfficer.getcourtOfficerListHtml($("#Case_Basic_ExecutionIntanceCourt").val());
        $(".divexecutionCourtClerkList").html(html);
        $("#hidCourtOfficerId").val("Case_Basic_ExecutionIntanceClerk");
        $("#hidCourtOfficerName").val("Case_Basic_ExecutionIntanceClerkName");

        $("#div_CourtOfficerList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 0,
            "top": $(tirgger).parent().position().top + 26,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#Case_Basic_LastIntanceJudgeName').on('click', '#Case_Basic_LastIntanceJudgeName', function () {
        var tirgger = this;
        var html = $.courtOfficer.getcourtOfficerListHtml($("#Case_Basic_LastIntanceCourt").val());
        $(".divlastCourtJudgeList").html(html);
        $("#hidCourtOfficerId").val("Case_Basic_LastIntanceJudge");
        $("#hidCourtOfficerName").val("Case_Basic_LastIntanceJudgeName");

        $("#div_CourtOfficerList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 0,
            "top": $(tirgger).parent().position().top + 26,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#Case_Basic_LastIntanceClerkName').on('click', '#Case_Basic_LastIntanceClerkName', function () {
        var tirgger = this;
        var html = $.courtOfficer.getcourtOfficerListHtml($("#Case_Basic_LastIntanceCourt").val());
        $(".divlastCourtClerkList").html(html);
        $("#hidCourtOfficerId").val("Case_Basic_LastIntanceClerk");
        $("#hidCourtOfficerName").val("Case_Basic_LastIntanceClerkName");

        $("#div_CourtOfficerList").css({
            "position": "absolute",
            "left": $(tirgger).parent().position().left + 0,
            "top": $(tirgger).parent().position().top + 26,
            "z-index": 9999
        }).toggle();

        return false;
    });

    $(document).off('click', '#div_CourtOfficerList ul li').on('click', '#div_CourtOfficerList ul li', function (e) {
        var courtOfficerId = $(this).find("a").attr("id");
        var courtOfficerName = $(this).find("a").text();
        var courtOfficerNameText = $(this).find("a").attr("text");
        var currentSelectedControl = $("#hidCourtOfficerName").val();
        var currentSelectedIdControl = $("#hidCourtOfficerId").val();

        if (currentSelectedControl == "Case_Basic_FirstIntanceJudgeName"){
            court.Courts.Court.CourtOfficer.AddIn(courtOfficerId, courtOfficerName, "firstCourtOfficer", currentSelectedControl);
        }
        else if(currentSelectedControl == "Case_Basic_FirstIntanceClerkName") {
            court.Courts.Court.CourtOfficer.AddIn(courtOfficerId, courtOfficerName, "firstCourtClerk", currentSelectedControl);
        }
        else if (currentSelectedControl == "Case_Basic_SecondIntanceJudgeName") {
            court.Courts.Court.CourtOfficer.AddIn(courtOfficerId, courtOfficerName, "secondCourtOfficer", currentSelectedControl);
        }
        else if (currentSelectedControl == "Case_Basic_SecondIntanceClerkName") {
            court.Courts.Court.CourtOfficer.AddIn(courtOfficerId, courtOfficerName, "secondCourtClerk", currentSelectedControl);
        }
        else if (currentSelectedControl == "Case_Basic_ExecutionIntanceJudgeName") {
            court.Courts.Court.CourtOfficer.AddIn(courtOfficerId, courtOfficerName, "executionCourtOfficer", currentSelectedControl);
        }
        else if (currentSelectedControl == "Case_Basic_ExecutionIntanceClerkName") {
            court.Courts.Court.CourtOfficer.AddIn(courtOfficerId, courtOfficerName, "executionCourtClerk", currentSelectedControl);
        }
        else if (currentSelectedControl == "Case_Basic_LastIntanceJudgeName"){
            court.Courts.Court.CourtOfficer.AddIn(courtOfficerId, courtOfficerName, "lastCourtOfficer", currentSelectedControl);
        }
        else if (currentSelectedControl == "Case_Basic_LastIntanceClerkName") {
            court.Courts.Court.CourtOfficer.AddIn(courtOfficerId, courtOfficerName, "lastCourtClerk", currentSelectedControl);
        }
        
        $("#div_CourtOfficerList").hide();
    });
    var firstIntanceCourt = new AssociateCourt(
        $("#div_FirstIntanceCourtList"),
        $("#Case_Basic_FirstIntanceCourt"),
        $("#Case_Basic_FirstIntanceCourtName"),
        $("#Case_Basic_FirstIntanceCaseNo"),
        null
    );
    var secondIntanceCourt = new AssociateCourt(
        $("#div_SecondIntanceCourtList"),
        $("#Case_Basic_SecondIntanceCourt"),
        $("#Case_Basic_SecondIntanceCourtName"),
        $("#Case_Basic_SecondIntanceCaseNo"),
        null
    );
    var executionIntanceCourt = new AssociateCourt(
        $("#div_ExecutionIntanceCourtList"),
        $("#Case_Basic_ExecutionIntanceCourt"),
        $("#Case_Basic_ExecutionIntanceCourtName"),
        $("#Case_Basic_ExecutionIntanceCaseNo"),
        null
    );
    var lastIntanceCourt = new AssociateCourt(
        $("#div_LastIntanceCourtList"),
        $("#Case_Basic_LastIntanceCourt"),
        $("#Case_Basic_LastIntanceCourtName"),
        $("#Case_Basic_LastIntanceCaseNo"),
        null
    );

    $(document).off('click', '.courtofficerremove').on('click', '.courtofficerremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        court.Courts.Court.CourtOfficer.Remove(this);
    });

    $(document).off('click', '.lawyerremove').on('click', '.lawyerremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Basic.CaseLawyer.Remove(this);
    });

    $(document).off('click', '#btnCaseCreate').on('click', '#btnCaseCreate', function () {
        c.Cases.Case.CreateUpdate();
    });

    $(document).off('click', '#btnCourtCreateUpdate').on('click', '#btnCourtCreateUpdate', function () {
        c.Cases.Case.Court.CreateUpdate();
    });

    $(document).off('click', '.btn_FirstIntanceJudge_add').on('click', '.btn_FirstIntanceJudge_add', function () {
        if ($("#Case_Basic_FirstIntanceCourt").val() == '')
        {
            $.showModalMessageBox("请选择一审法院.");
            return false;
        }
        court.Courts.Court.CourtOfficer.Open($("#Case_Basic_FirstIntanceCourt").val(), court.Courts.Court.CourtOfficer.CreateUpdate_CallBack_FirstIntanceJudge);
    });

    $(document).off('click', '.btn_FirstIntanceClerk_add').on('click', '.btn_FirstIntanceClerk_add', function () {
        if ($("#Case_Basic_FirstIntanceCourt").val() == '') {
            $.showModalMessageBox("请选择一审法院.");
            return false;
        }
        court.Courts.Court.CourtOfficer.Open($("#Case_Basic_FirstIntanceCourt").val(), court.Courts.Court.CourtOfficer.CreateUpdate_CallBack_FirstIntanceClerk);
    });

    $(document).off('click', '.btn_SecondIntanceJudge_add').on('click', '.btn_SecondIntanceJudge_add', function () {
        if ($("#Case_Basic_SecondIntanceCourt").val() == '') {
            $.showModalMessageBox("请选择二审法院.");
            return false;
        }
        court.Courts.Court.CourtOfficer.Open($("#Case_Basic_SecondIntanceCourt").val(), court.Courts.Court.CourtOfficer.CreateUpdate_CallBack_SecondIntanceJudge);
    });

    $(document).off('click', '.btn_SecondIntanceClerk_add').on('click', '.btn_SecondIntanceClerk_add', function () {
        if ($("#Case_Basic_SecondIntanceCourt").val() == '') {
            $.showModalMessageBox("请选择二审法院.");
            return false;
        }
        court.Courts.Court.CourtOfficer.Open($("#Case_Basic_SecondIntanceCourt").val(), court.Courts.Court.CourtOfficer.CreateUpdate_CallBack_SecondIntanceClerk);
    });

    $(document).off('click', '.btn_LastIntanceJudge_add').on('click', '.btn_LastIntanceJudge_add', function () {
        if ($("#Case_Basic_LastIntanceCourt").val() == '') {
            $.showModalMessageBox("请选择再审法院.");
            return false;
        }
        court.Courts.Court.CourtOfficer.Open($("#Case_Basic_LastIntanceCourt").val(), court.Courts.Court.CourtOfficer.CreateUpdate_CallBack_LastIntanceJudge);
    });

    $(document).off('click', '.btn_LastIntanceClerk_add').on('click', '.btn_LastIntanceClerk_add', function () {
        if ($("#Case_Basic_LastIntanceCourt").val() == '') {
            $.showModalMessageBox("请选择再审法院.");
            return false;
        }
        court.Courts.Court.CourtOfficer.Open($("#Case_Basic_LastIntanceCourt").val(), court.Courts.Court.CourtOfficer.CreateUpdate_CallBack_LastIntanceClerk);
    });

    $(document).off('click', '.btn_ExecutionIntanceJudge_add').on('click', '.btn_ExecutionIntanceJudge_add', function () {
        if ($("#Case_Basic_ExecutionIntanceCourt").val() == '') {
            $.showModalMessageBox("请选择执行法院.");
            return false;
        }
        court.Courts.Court.CourtOfficer.Open($("#Case_Basic_ExecutionIntanceCourt").val(), court.Courts.Court.CourtOfficer.CreateUpdate_CallBack_ExecutionIntanceJudge);
    });

    $(document).off('click', '.btn_ExecutionIntanceClerk_add').on('click', '.btn_ExecutionIntanceClerk_add', function () {
        if ($("#Case_Basic_ExecutionIntanceCourt").val() == '') {
            $.showModalMessageBox("请选择执行法院.");
            return false;
        }
        court.Courts.Court.CourtOfficer.Open($("#Case_Basic_ExecutionIntanceCourt").val(), court.Courts.Court.CourtOfficer.CreateUpdate_CallBack_ExecutionIntanceClerk);
    });

    $(document).off('click', '#FirstInstace').on('click', '#FirstInstace', function () {
        if ($(this).prop("checked") == true) {
            $("#divFirstInstace_Court").show();
            $("#divFirstInstace_ProcuratorateUnit").show();
        }
        else {
            $("#divFirstInstace_Court").hide();
            $("#divFirstInstace_ProcuratorateUnit").hide();
        }
    });

    $(document).off('click', '#SecondInstace').on('click', '#SecondInstace', function () {
        if ($(this).prop("checked") == true) {
            $("#divSecondInstace_Court").show();
            $("#divSecondInstace_ProcuratorateUnit").show();
        }
        else {
            $("#divSecondInstace_Court").hide();
            $("#divSecondInstace_ProcuratorateUnit").hide();
        }
    });

    $(document).off('click', '#LastInstace').on('click', '#LastInstace', function () {
        if ($(this).prop("checked") == true) {
            $("#divLastInstace_Court").show();
            $("#divLastInstace_ProcuratorateUnit").show();
        }
        else {
            $("#divLastInstace_Court").hide();
            $("#divLastInstace_ProcuratorateUnit").hide();
        }
    });
});