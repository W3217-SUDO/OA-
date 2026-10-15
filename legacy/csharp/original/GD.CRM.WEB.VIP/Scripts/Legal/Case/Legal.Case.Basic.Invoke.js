$(document).ready(function () {

    $(document).click(function () {
     });

    var customter = new AssociateCustomer(
        $("#div_customer"),
        $("#Case_Basic_CustomerNo"),
        $("#Case_Basic_CustomerNo"),
        $("#Case_Basic_CustomerName"),
        contract.Contracts.List,
        investigationClue.InvestigationClues.List
    );

    var _courtLawyer = new AssociateAvailableUser_Laywer(
        $("#div_courtlawyerlist"),
        $("#Case_Basic_CourtLawyer_Input"),
        $("#Case_Basic_CourtLawyer_Input"),
        c.Cases.Case.Basic.CourtLawyer.AddIn
    );

    var caseLawyer = new AssociateAvailableUser_Laywer(
        $("#div_lawyerlist"),
        $("#Case_Basic_CaseLawyer_Input"),
        $("#Case_Basic_CaseLawyer_Input"),
        c.Cases.Case.Basic.CaseLawyer.AddIn
    );

    var caseAssistant = new AssociateAvailableUser_Laywer(
        $("#div_assistantlist"),
        $("#Case_Basic_CaseAssistant_Input"),
        $("#Case_Basic_CaseAssistant_Input"),
        c.Cases.Case.Basic.CaseAssistant.AddIn
    );

    var caseInvestigator = new AssociateAvailableUser_Laywer(
        $("#div_investigatorlist"),
        $("#Case_Basic_Investigator_Input"),
        $("#Case_Basic_Investigator_Input"),
        c.Cases.Case.Basic.Investigator.AddIn
    );

    var caseBusinessOwner = new AssociateAvailableUser_Laywer(
        $("#div_businessownerlist"),
        $("#Case_Basic_BusinessOwner_Input"),
        $("#Case_Basic_BusinessOwner_Input"),
        c.Cases.Case.Basic.BusinessOwner.AddIn
    );

    var cause = new AssociateCause(
        $("#div_cause"),
        $("#Case_Basic_CauseName_Input"),
        $("#Case_Basic_CauseName_Input"),
         c.Cases.Case.Basic.Cause.AddIn
    );
    
    $(window).resize(function () {
        //c.ResetSize();
    });

    $(document).off('click', '.lawyerremove').on('click', '.lawyerremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Basic.CaseLawyer.Remove(this);
    });

    $(document).off('click', '.assistantremove').on('click', '.assistantremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Basic.CaseAssistant.Remove(this);
    });

    $(document).off('click', '.investigatorremove').on('click', '.investigatorremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Basic.Investigator.Remove(this);
    });

    $(document).off('click', '.businessownerremove').on('click', '.businessownerremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Basic.BusinessOwner.Remove(this);
    });

    $(document).off('click', '.causeremove').on('click', '.causeremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.Basic.Cause.Remove(this);
    });

    $(document).off('click', '#btnCaseCreate').on('click', '#btnCaseCreate', function () {
        c.Cases.Case.CreateUpdate();
    });

    $(document).off('click', '.btn_customer_add').on('click', '.btn_customer_add', function () {
        $.customer.Open(this);
    });

    $("#Case_Basic_InvestigationClueNo").chosen({
        width: '100%',
        disable_search: false,
        search_contains: true
    });

    $(document).off('click', '#btnClueGenerateCaseCreate').on('click', '#btnClueGenerateCaseCreate', function () {
        c.Cases.Case.ClueToCase_CreateUpdate(c.Cases.Case.ClueToCase_CreateUpdate_NextStep);
    });
});