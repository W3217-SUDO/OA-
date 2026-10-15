$(document).ready(function () {

    $(document).click(function () {
     });

    var caseAppellant = new AssociateLitigant(
        $("#div_appellantlist"),
        $("#Case_Basic_Appellant_Input"),
        $("#Case_Basic_Appellant_Input"),
        $("#Case_Basic_Appellant_Input"),
        c.Cases.Case.Litigant.Appellant.AddIn
    );

    var caseAppellee = new AssociateLitigant(
        $("#div_appelleelist"),
        $("#Case_Basic_Appellee_Input"),
        $("#Case_Basic_Appellee_Input"),
        $("#Case_Basic_Appellee_Input"),
        c.Cases.Case.Litigant.Appellee.AddIn
    );
    

    var caseTheThird = new AssociateLitigant(
        $("#div_thethirdlist"),
        $("#Case_Basic_TheThird_Input"),
        $("#Case_Basic_TheThird_Input"),
        $("#Case_Basic_TheThird_Input"),
        c.Cases.Case.Litigant.TheThird.AddIn
    );

    $(document).off('click', '.btn_appellantagent_add').on('click', '.btn_appellantagent_add', function () {
        c.Cases.Case.Litigant.Appellant.LitigantAgent.Open($("#Case_Basic_AppellantAgent_Input"));
    });

    $(document).off('click', '#Case_Basic_AppellantAgent_Input').on('click', '#Case_Basic_AppellantAgent_Input', function () {
        c.Cases.Case.Litigant.Appellant.LitigantAgent.Open($("#Case_Basic_AppellantAgent_Input"));
    });

    $(document).off('click', '.btn_appelleeagent_add').on('click', '.btn_appelleeagent_add', function () {
        c.Cases.Case.Litigant.Appellee.LitigantAgent.Open($("#Case_Basic_AppelleeAgent_Input"));
    });

    $(document).off('click', '#Case_Basic_AppelleeAgent_Input').on('click', '#Case_Basic_AppelleeAgent_Input', function () {
        c.Cases.Case.Litigant.Appellee.LitigantAgent.Open($("#Case_Basic_AppelleeAgent_Input"));
    });


    $(document).off('click', '.btn_thethird_add').on('click', '.btn_thethird_add', function () {
        $.customer.Open(c.Cases.Case.Litigant.TheThird.AddIn);
    });

    $(document).off('click', '#Case_Basic_TheThirdAgent_Input').on('click', '#Case_Basic_TheThirdAgent_Input', function () {
        c.Cases.Case.Litigant.TheThird.LitigantAgent.Open($("#Case_Basic_TheThirdAgent_Input"));
    });

    $(document).off('click', '.btn_appellant_add').on('click', '.btn_appellant_add', function () {
        $.customer.Open(c.Cases.Case.Litigant.Appellant.AddIn);
    });

    $(document).off('click', '.btn_appellee_add').on('click', '.btn_appellee_add', function () {
        $.customer.Open(c.Cases.Case.Litigant.Appellee.AddIn);
    });

    $(document).off('click', '.appellantremove').on('click', '.appellantremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Litigant.Appellant.Remove(this);
    });

    $(document).off('click', '.appellantagentremove').on('click', '.appellantagentremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Litigant.Appellant.LitigantAgent.Remove(this);
    });

    $(document).off('click', '.appelleeremove').on('click', '.appelleeremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Litigant.Appellee.Remove(this);
    });

    $(document).off('click', '.appelleeagentremove').on('click', '.appelleeagentremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Litigant.Appellee.LitigantAgent.Remove(this);
    });

    $(document).off('click', '.thethirdremove').on('click', '.thethirdremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Litigant.TheThird.Remove(this);
    });

    $(document).off('click', '.thethirdagentremove').on('click', '.thethirdagentremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Litigant.TheThird.LitigantAgent.Remove(this);
    });

    $(document).off('click', '#btnLitigantAgent').on('click', '#btnLitigantAgent', function () {

        if ($("#LitigantAgentInput").val() == 'Case_Basic_AppellantAgent_Input')
        {
            c.Cases.Case.Litigant.Appellant.LitigantAgent.CreateUpdate(c.Cases.Case.Litigant.Appellant.LitigantAgent.AddIn, $("#Case_Basic_AppellantAgent_Input"));
        }
        else if ($("#LitigantAgentInput").val() == 'Case_Basic_AppelleeAgent_Input') {
            c.Cases.Case.Litigant.Appellee.LitigantAgent.CreateUpdate(c.Cases.Case.Litigant.Appellee.LitigantAgent.AddIn, $("#Case_Basic_AppelleeAgent_Input"));
        }
        else if ($("#LitigantAgentInput").val() == 'Case_Basic_TheThirdAgent_Input') {
            c.Cases.Case.Litigant.TheThird.LitigantAgent.CreateUpdate(c.Cases.Case.Litigant.TheThird.LitigantAgent.AddIn, $("#Case_Basic_TheThirdAgent_Input"));
        }
    });

    $(document).off('click', '#btnLitigantCreateUpdateNext').on('click', '#btnLitigantCreateUpdateNext', function () {
        c.Cases.Case.Litigant.CreateUpdate(c.Cases.Case.Litigant.CreateUpdate_NextStep);
    });

    $(document).off('click', '#btnLitigantCreateUpdate').on('click', '#btnLitigantCreateUpdate', function () {
        c.Cases.Case.Litigant.CreateUpdate(c.Cases.Case.Litigant.CreateUpdate_Refersh);
    });

    $(document).off('click', '.bootstrap-tagsinput.appellantAgent').on('click', '.bootstrap-tagsinput.appellantAgent', function () {
        $(":input", this).focus();
        c.Cases.Case.Litigant.Appellant.LitigantAgent.Open($("#Case_Basic_AppellantAgent_Input"));
    });

    $(document).off('click', '.bootstrap-tagsinput.appelleeAgent').on('click', '.bootstrap-tagsinput.appelleeAgent', function () {
        $(":input", this).focus();
        c.Cases.Case.Litigant.Appellee.LitigantAgent.Open($("#Case_Basic_AppelleeAgent_Input"));
    });

    $(document).off('click', '.bootstrap-tagsinput.theThirdAgent').on('click', '.bootstrap-tagsinput.theThirdAgent', function () {
        $(":input", this).focus();
        c.Cases.Case.Litigant.TheThird.LitigantAgent.Open($("#Case_Basic_TheThirdAgent_Input"));
    });

});