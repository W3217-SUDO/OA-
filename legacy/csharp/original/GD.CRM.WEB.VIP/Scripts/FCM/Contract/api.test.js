$(document).ready(function () {
    $("#btnContractListTest").click(function () {
        GetResourceOwnerCredentialsAccessToken();
    });

    $("#btnContractView").click(function () {

        var data = {
            id: 18,
         };

        

        $.ajaxPost("http://localhost/Dchien.Legal.Web.Api/api/Contract/GetContract", data, function (response) {
            if (response.IsSuccess) {
                
            } else {
                
            }
        });
    });
});


function GetOpenId() {
    $.ajax({
        url: "http://localhost/Dchien.Legal.Web.Api/api/WxAccount/GetOpenId",
        type: "post",
        data: {
            "JsCode": "sample string 1",
            "EncryptedData": "sample string 2",
            "Iv": "sample string 3"
        },
        dataType: "json",
        success: function (data) {
          
        }
    });
}

function GetResourceOwnerCredentialsAccessToken() {
    $("#resourceOwnerresult").html("Requesting");
    var clientId = "10000001002";
    var clientSecret = "REDACTED_ARCHIVE_ONLY";

    debugger
    $.ajax({
        url: "http://localhost/Dchien.Legal.Web.Api/Token",
        type: "post",
        data: {
            "grant_type": "password",
            "REDACTED_ARCHIVE_ONLY": "REDACTED_ARCHIVE_ONLY",
            "password": "REDACTED_ARCHIVE_ONLY",
            "openid": "REDACTED_ARCHIVE_ONLY"
        },
        dataType: "json",
        headers: {
            "Authorization": "REDACTED_ARCHIVE_ONLY" + Base64_Encode(clientId + ":" + clientSecret),
        },
        success: function (data) {

            debugger
            var accessToken = data.access_token;
            
            GetContractList(accessToken);
        }
    });
 
}


function GetContractList(accessToken) {

    debugger
    var html = "Token:" + accessToken + "<br/><br/>";
    $.ajax({
        url: "http://localhost/Dchien.Legal.Web.Api/api/Case/GetCaseListByBusinessOwner",
        type: "post",

        data:{
            "Keyword": "",
            "PageNo": 1,
            "PageSize": 20,
            "Id": 4,
            "OpenId": "REDACTED_ARCHIVE_ONLY"
        },

        dataType: "json",
        headers: {
            "Authorization": "REDACTED_ARCHIVE_ONLY" + accessToken
        },


        success: function (data) {
            
            debugger
    
        }
    });
}


function GetCurrentUserName(accessToken) {
    var html = "Token:" + accessToken + "<br/><br/>";
    $.ajax({
        url: "http://localhost/Dchien.Legal.Web.Api/api/WxAccount/GetCurrent",
        type: "get",
        dataType: "text",
        headers: {
            "Authorization": "REDACTED_ARCHIVE_ONLY" + accessToken
        },
        success: function (userName) {
            
            debugger
            html += "CurrentUserName:" + userName + "<br/>";
            $("#resourceOwnerresult").html(html);
        }
    });
}

function Base64_Encode(str) {
    var c1, c2, c3;
    var base64EncodeChars = "REDACTED_ARCHIVE_ONLY";
    var i = 0, len = str.length, string = '';

    while (i < len) {
        c1 = str.charCodeAt(i++) & 0xff;
        if (i === len) {
            string += base64EncodeChars.charAt(c1 >> 2);
            string += base64EncodeChars.charAt((c1 & 0x3) << 4);
            string += "==";
            break;
        }
        c2 = str.charCodeAt(i++);
        if (i === len) {
            string += base64EncodeChars.charAt(c1 >> 2);
            string += base64EncodeChars.charAt(((c1 & 0x3) << 4) | ((c2 & 0xF0) >> 4));
            string += base64EncodeChars.charAt((c2 & 0xF) << 2);
            string += "=";
            break;
        }
        c3 = str.charCodeAt(i++);
        string += base64EncodeChars.charAt(c1 >> 2);
        string += base64EncodeChars.charAt(((c1 & 0x3) << 4) | ((c2 & 0xF0) >> 4));
        string += base64EncodeChars.charAt(((c2 & 0xF) << 2) | ((c3 & 0xC0) >> 6));
        string += base64EncodeChars.charAt(c3 & 0x3F);
    }

    
    return string;
}