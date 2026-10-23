$(document).ready(function () {

    $(document).click(function () {
     });
 
    $("#Case_Basic_CustomerAddIn_Contacts").chosen({
        width: '100%',
        disable_search: false,
        search_contains: true
    });
 

    $(document).off('click', '.lawyerremove').on('click', '.lawyerremove', function () {
        if ($(this).parents(".bootstrap-tagsinput").find("input").attr("disabled") == 'disabled') {
            return false;
        }
        c.Cases.Case.CustomerAddIn.Operator.Remove(this);
    });

    
    $(document).off('click', '#lnkCustomerAddInOperatorAdd').on('click', '#lnkCustomerAddInOperatorAdd', function () {
        c.Cases.Case.CustomerAddIn.Operator.Open();
    });

    //$(document).off('click', '#btnCourtCreateUpdate').on('click', '#btnCourtCreateUpdate', function () {
    //    c.Cases.Case.Court.CreateUpdate();
    //});

    
});