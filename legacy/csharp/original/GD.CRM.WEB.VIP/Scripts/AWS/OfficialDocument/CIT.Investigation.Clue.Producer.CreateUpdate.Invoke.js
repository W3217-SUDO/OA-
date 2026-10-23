 

function init()
{
    var province = $("#Customer_CustomerBasic_Province").val();
    var city = $("#Customer_CustomerBasic_City").val();
    $('#district').citys({ code: city });

    $('#district').citys({ code: city });
}

$(document).ready(function () {
   
    $('#producer_district').citys();

  
});