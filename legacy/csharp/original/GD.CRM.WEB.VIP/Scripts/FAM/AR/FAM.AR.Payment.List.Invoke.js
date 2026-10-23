$(document).ready(function () {
    
    if ($("#SearchCondition_PageId").val() == '5001001002') {
        payment.List.PaymentList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001001003') {
        payment.List.PaymentPublicList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001001004') {
        payment.List.PaymentApplyList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001001005') {
        payment.List.PaymentAppliedList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001007001') {
        
        payment.Payment.Settlement.PendingList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001007002') {
        payment.Payment.Settlement.ProcessingList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001007003') {
        payment.Payment.Settlement.PendingPaymentList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001007004') {
        payment.Payment.Settlement.ProcessedList();
    }
    else if ($("#SearchCondition_PageId").val() == '5001007005') {
        payment.Payment.Settlement.RejectedList();
    }

    $(".aps-icon-shangjiantou").off().on("click", function () {
        var sorting = $(this).parent().attr("data-field");
        if (sorting != null && sorting != '') {
            $(".aps-sort").each(function (i, e) {
                $(e).removeClass("aps-asc");
                $(e).removeClass("aps-desc");
            });

            $(this).parent().addClass("aps-asc");
            $("#SearchCondition_Sorting").val(sorting + " asc");
        }

        if ($("#SearchCondition_PageId").val() == '5001001002') {
            payment.List.PaymentList();
        }
        else if ($("#SearchCondition_PageId").val() == '5001001003') {
            payment.List.PaymentPublicList();
        }
        else if ($("#SearchCondition_PageId").val() == '5001001004') {
            payment.List.PaymentApplyList();
        }
        else if ($("#SearchCondition_PageId").val() == '5001001005') {
            payment.List.PaymentAppliedList();
        }

        
    });

    $(".aps-icon-xiajiantou").off().on("click", function () {
        var sorting = $(this).parent().attr("data-field");
        if (sorting != null && sorting != '') {
            $(".aps-sort").each(function (i, e) {
                $(e).removeClass("aps-asc");
                $(e).removeClass("aps-desc");
            });
            $(this).parent().addClass("aps-desc");
            $("#SearchCondition_Sorting").val(sorting + " desc");
        }
        if ($("#SearchCondition_PageId").val() == '5001001002') {
            payment.List.PaymentList();
        }
        else if ($("#SearchCondition_PageId").val() == '5001001003') {
            payment.List.PaymentPublicList();
        }
        else if ($("#SearchCondition_PageId").val() == '5001001004') {
            payment.List.PaymentApplyList();
        }
        else if ($("#SearchCondition_PageId").val() == '5001001005') {
            payment.List.PaymentAppliedList();
        }
    });
});