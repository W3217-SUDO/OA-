/// <reference path="jquery.js" />

(function ($) {
    //form调用ajax, url:连接的Ashx地址、func：回调函数function(response, success){}
    $.fn.extend({
        ajaxPost: function (url, func) {
            var request = $(this).serialize();
            $.ajaxPost(url, request, func);
        }
    });

    $.ajaxPostJson = function (url, requestData, func, isShowLoading) {
        if (!$.isFunction(func)) {
            alert("传入的回调方法参数func，不是方法。请检查调用的地方！！");
            return;
        }

        
        if (isShowLoading == null || isShowLoading) {
            $.openLoading();
        }
        $.ajax({
            type: "post",
            url: url,
            data: requestData,
            dataType: "json",
            contentType: 'application/json; charset=utf-8',
            cache: false,
            success: function(responseData, textStatus, jqXHR) {
                var postResponse = {};
                if (jqXHR.getResponseHeader("Content-Type").split(";")[0] === "application/json") {
                    postResponse = responseData;
                } else {
                    postResponse.IsSuccess = true;
                    postResponse.Message = "";
                    postResponse.Data = responseData;
                }
                //setTimeout(function () { $.closeLoading(); func(postResponse) }, 500);
                if (isShowLoading == null || !isShowLoading) {
                    $.closeLoading();
                }
                func(postResponse);
            },
            error: function (jqXHR, textStatus, errorThrown) {

                //setTimeout(function () { $.closeLoading(); $.showModalMessageBox(jqXHR.status + " " + jqXHR.statusText) }, 500);
                if (isShowLoading == null || isShowLoading) {
                    $.closeLoading();
                }
                //$.showModalMessageBox(jqXHR.status + " " + jqXHR.statusText);
                $.showModalMessageBox("非常抱歉，系统调整中……<br />(Error Code:" + jqXHR.status + ")");
            }
        });
    };

    $.ajaxPost = function (url, requestData, func, isShowLoading) {
        if (!$.isFunction(func)) {
            alert("传入的回调方法参数func，不是方法。请检查调用的地方！！");
            return;
        }
        if (isShowLoading == null || isShowLoading) {
            $.openLoading();
        }
        $.ajax({
            type: "post",
            url: url,
            data: requestData,
            cache: false,
            traditional: true,
            success: function (responseData, textStatus, jqXHR) {
                var postResponse = {};
                if (jqXHR.getResponseHeader("Content-Type").split(";")[0] === "application/json") {
                    postResponse = responseData;
                } else {
                    postResponse.IsSuccess = true;
                    postResponse.Message = "";
                    postResponse.Data = responseData;
                }
                //setTimeout(function () { $.closeLoading(); func(postResponse) }, 500);
                if (isShowLoading == null || !isShowLoading) {
                    $.closeLoading();
                }
                // if error show error message
                if (postResponse.IsSuccess == false) {
                    //$.showModalMessageBox(postResponse.Message);
                }

                func(postResponse);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                
                //setTimeout(function () { $.closeLoading(); $.showModalMessageBox(jqXHR.status + " " + jqXHR.statusText) }, 500);
                if (isShowLoading == null || isShowLoading) {
                    $.closeLoading();
                }
                //$.showModalMessageBox(jqXHR.status + " " + jqXHR.statusText);
                $.showModalMessageBox("非常抱歉，系统调整中……<br />(Error Code:" + jqXHR.status + ")");
            }
        });
    };

    $.ajaxPostMessage = function (url, requestData, func, isShowLoading) {

        if (!$.isFunction(func)) {
            alert("传入的回调方法参数func，不是方法。请检查调用的地方！！");
            return;
        }
        if (isShowLoading == null || isShowLoading) {
            $.openLoading();
        }
        $.ajax({
            type: "post",
            url: url,
            data: requestData,
            cache: false,
            traditional: true,
            success: function (responseData, textStatus, jqXHR) {
                var postResponse = {};
                if (jqXHR.getResponseHeader("Content-Type").split(";")[0] === "application/json") {
                    postResponse = responseData;
                } else {
                    postResponse.IsSuccess = true;
                    postResponse.Message = "";
                    postResponse.Data = responseData;
                }
                //setTimeout(function () { $.closeLoading(); func(postResponse) }, 500);
                if (isShowLoading == null || !isShowLoading) {
                    $.closeLoading();
                }
                // if error show error message
                if (postResponse.IsSuccess == false) {
                    //$.showModalMessageBox(postResponse.Message);
                }

                func(postResponse);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                //setTimeout(function () { $.closeLoading(); $.showModalMessageBox(jqXHR.status + " " + jqXHR.statusText) }, 500);
                if (isShowLoading == null || isShowLoading) {
                    $.closeLoading();
                }
                //$.showModalMessageBox(jqXHR.status + " " + jqXHR.statusText);
                //$.showModalMessageBox("非常抱歉，系统调整中……<br />(Error Code:" + jqXHR.status + ")");
            }
        });
    };

    //form调用ajax, url:连接的Ashx地址、func：回调函数function(response, success){}
    $.fn.extend({
        ajaxJson: function (url, func) {
            var jsonObj = $(this).serializeObject();
            $.ajaxJson(url, jsonObj, func);
        }
    });

    $.ajaxJson = function (url, jsonObj, func) {
        //var request = JSON.stringify(jsonObj);
        var request = $.toJSON(jsonObj);
        $.ajaxPost(url, request, func);
    }


    //鼠标提示框
    $.addTips = function (srcElem, p) {
        var g = {
            setting: {},
            show: function () {
                var content = g.src.attr("mod_jmpinfo_content");  //提示内容
                if (content == null) {
                    content = g.src.parent().find("span").attr("mod_jmpinfo_content")
                }
                if (content == null) return;
                var tip = $("#tuna_jmpinfo");
                if (tip.length) {

                    tip.find("div.jmp_bd:first").html(content);
                    tip.css({
                        top: parseInt(g.src.position().top + 20),
                        left: parseInt(g.src.position().left)
                    });
                    tip.show();
                } else {

                    var tips = "<div id=\"tuna_jmpinfo\" style=\"position: absolute; z-index: 120;left:" + parseInt(g.src.position().left) + "px;top:" + parseInt(g.src.position().top + 20) + "px\">";
                    tips += "<div class=\"base_jmp jmp_text base_jmp_t\" style=\"width: 340px;\">";
                    tips += "<b class=\"tri_t\" style=\"left: 16px;\"></b>";
                    tips += "<div class=\"jmp_bd\">";
                    tips += content;
                    tips += "</div>";
                    tips += "</div>";
                    tips += "</div>";

                    $(document.body).append($(tips));
                }
            },
            hide: function () {
                var tip = $("#tuna_jmpinfo");
                if (tip.length) {
                    tip.hide();
                }
            }
        };

        g.setting = p || {
            containerId: "tuna_jmpinfo"
        };

        g.src = srcElem;
        g.src.mouseover(function () {
            g.show();
        });
        g.src.mouseout(function () {
            g.hide();
        });

        //        $(document).click(function () { g.hide(); });
        return g;
    };

    $.showNotice = function () {
        $("TEXTAREA,input[mod-notice-tip]").each(function () {
            if ($(this).val() == "" || $(this).val() == $(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            }
            if ($(this).attr("mod-notice-tip") != null) {
                if ($(this).val() == "" || $(this).val() == $(this).attr("mod-notice-tip")) {
                    $(this).val($(this).attr("mod-notice-tip")).css("color", "#979393");
                }
                $(this).focus(function () {
                    if ($(this).val() == $(this).attr("mod-notice-tip")) {
                        $(this).val('');
                        $(this).val('').css("color", "#333333");
                    }
                });
                $(this).blur(function () {
                    if ($(this).val() == "") {
                        $(this).val($(this).attr("mod-notice-tip"));
                        $(this).val($(this).attr("mod-notice-tip")).css("color", "#979393");
                    }
                });
            }
        });
    }

    //contetn为要显示的内容  
    //height为离窗口顶部的距离  
    //time为多少秒后关闭的时间，单位为秒  
    $.showTips = function (content, height, time) {
        //窗口的宽度  
        var windowWidth  = $(window).width();  
        var tipsDiv = '<div class="tipsClass">' + content + '</div>';   
        $( 'body' ).append( tipsDiv );  
        $( 'div.tipsClass' ).css({  
            'top'       : height + 'px',  
            'left'      : ( windowWidth / 2 ) - 350/2 + 'px',  
            'position'  : 'absolute',  
            'padding'   : '3px 5px',  
            'background': '#666',
            'font-size' : 12 + 'px',  
            'margin'    : '0 auto',  
            'text-align': 'center',  
            'width'     : '350px',  
            'height'    : 'auto',  
            'color'     : '#fff',  
            'opacity': '0.8',
            'z-index':"999999"
        }).show();  
        setTimeout( function(){$( 'div.tipsClass' ).fadeOut();}, ( time * 1000 ) );  
    }   
 

    $.openLoading = function () {
        var div = {
            show: function () {
                if ($(".loadingDiv").length) {
                    var newwidth = document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width();
                    newwidth = newwidth + $(document).scrollLeft();
                    $(".loadingDiv").css({ width: newwidth + 'px', height: $(document).height() + 'px' });
                    $(".loadingDiv").show();
                } else {
                    $(document.body).append(div.mask);
                }
                if ($("#divProcessingBar").length) {
                    $("#divProcessingBar").remove();
                    $(document.body).append(div.processingBar);
                } else {
                    $(document.body).append(div.processingBar);
                }

                var top = 0;
                if ($(window).scrollTop() > 0) {
                    top = $(window).height() + $(window).scrollTop() - ($(window).height() + div.processingBar.height()) / 2;
                } else {
                    top = ($(window).height() - div.processingBar.height()) / 2
                }

                div.processingBar.css({
                    "position": "absolute",
                    "left": ($(document.body).width() - 300) / 2,
                    "top": top,
                    "z-index": 1200
                }).show();
            }
        };

        div.mask = $("<div class='loadingDiv' id='loadingDiv'></div>")
           .css({
               "background-Color": "rgb(255, 255, 255)",
               "position": "absolute",
               "border": "medium none",
               "left": 0,
               "right": 0,
               "top": 0,
               "bottom": 0,
               "-moz-opacity": 0.4,
               "opacity": 0.4,
               "filter": "alpha(opacity=40)",
               "z-index": 1100,
               "width": (document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width()) + $(document).scrollLeft(),
               "height": $(window).height() > $(document.body).height() ? $(window).height() : $(document.body).height()
           });

        var imgsrc = AP_ROOT + "Resource/css/images/loading_50.gif";
        div.processingBar = $("<div id=\"divProcessingBar\" class=\"c_mask\"><div class=\"c_mask_bd c_loading\"><img src=\"" + imgsrc + " \" alt=\"\"><strong class=\"font16\">系统处理中，请稍后...</strong></div></div>")
            .css({
                "width": "300px"
            });
        div.show();
        MaskCenter($("#loadingDiv"));
        center($("#divProcessingBar"));
    }

    $.closeLoading = function () {
        if ($(".loadingDiv").length) {
            //setTimeout(function () { $(".loadingDiv").hide(); $("#divProcessingBar").hide(); }, 500);
            $(".loadingDiv").hide();
            $("#divProcessingBar").hide();
        }
    }

    $.showModalMessageBox = function (msg, url, disableautohide,widthstr) {
        this.hrefurl = url;
        var div = {
            show: function () {
 
                if ($("#divMessageBox").length) {
                    $("#divMessageBox").remove();
                    $(document.body).append(div.messageBox);
                } else {
                    $(document.body).append(div.messageBox);
                }
                 $('#divMessageBox').modal({ backdrop: 'static', keyboard: false });
                $('#divMessageBox').on('hidden.bs.modal', function () {
                    $("#divMessageBox").remove();
                });
             }
        };

        div.messageBox = $("<div tabindex='-1' id='divMessageBox' class='modal fade' ><div class='modal-dialog'><div class='modal-content'><div class='ng-scope'><div class='modal-header'><button type='button' class='close' data-dismiss='modal' data-ng-click='close(false)' aria-hidden='true'>×</button><h5 class='modal-title ng-binding'>提示</h5></div><div class='modal-body'><div><span class='text-size-32 icon-warning-1 text-info' style='color: #09c'></span> <span style='display:inline;margin-bottom: 10px;margin-left: 10px;vertical-align:6px;font-size: 18px' >" + msg + "</span></div></div><div class='modal-footer'><button class='btn btn-primary' id='btnShowMessage' onclick=\"$.hideModalMessageBox()\">确定</button></div></div></div></div></div>");
        div.show();

        $("#divMessageBox").focus();

        if (!disableautohide) {
            $(document).keyup(function (event) {
                if (event.keyCode == 13) {
                    $.hideModalMessageBox();
                }
            });
        }

    }

    $.hideModalMessageBox = function () {
        $('#divMessageBox').modal('hide');
        if (this.hrefurl != null) {
            location.href = this.hrefurl;
        }
    }

    //弹出confirm优化页面start
    //msg 提示消息文字(不为空)
    //functionCallback 回调function(不为空)
    //heightstr 提示框高度(可为空)
    //widthstr 提示框宽度(可为空)
    //obj 回调function(obj)的参数(可为空)
    $.showModalConfirmDialog = function (msg, functionCallback, obj, notshowcancel, disableautohide,heightstr, widthstr) {
        this.objStr = obj;
        var div = {
            show: function () {
                if ($("#divConfirmDialog").length) {
                    $('#divConfirmDialog').modal('hide');
                    $(document.body).append(div.messageBox);
                } else {
                    $(document.body).append(div.messageBox);
                }
                $('#divConfirmDialog').modal({ backdrop: 'static', keyboard: false });
                $('#divConfirmDialog').on('hidden.bs.modal', function () {
                    $("#divConfirmDialog").remove();
                });
            }
        };
        if (notshowcancel) {
            div.messageBox = $("<div  class='modal fade' id='divConfirmDialog' ><div class='modal-dialog'><div class='modal-content'><div class='ng-scope'><div class='modal-header'><button type='button' class='close' data-dismiss='modal' data-ng-click='close(false)' aria-hidden='true'>×</button><h5 class='modal-title ng-binding'>提示</h5></div><div class='modal-body'><div><span class='text-size-32 icon-warning-1 text-info' style='color: #09c'></span> <span style='display:inline;margin-bottom: 10px;margin-left: 10px;vertical-align:6px;font-size: 18px' >" + msg + "</span></div></div><div class='modal-footer'><button class='btn btn-primary' id='btnShowMessage' onclick=\"$.sureModalConfirmDialog(" + functionCallback + ")\">确定</button></div></div></div></div></div>");
        } else {
            div.messageBox = $("<div  class='modal fade' id='divConfirmDialog' ><div class='modal-dialog'><div class='modal-content'><div class='ng-scope'><div class='modal-header'><button type='button' class='close' data-dismiss='modal' data-ng-click='close(false)' aria-hidden='true'>×</button><h5 class='modal-title ng-binding'>提示</h5></div><div class='modal-body'><div><span class='text-size-32 icon-warning-1 text-info' style='color: #09c'></span> <span style='display:inline;margin-bottom: 10px;margin-left: 10px;vertical-align:6px;font-size: 18px' >" + msg + "</span></div></div><div class='modal-footer'><button class='btn btn-primary' id='btnShowMessage' onclick=\"$.sureModalConfirmDialog(" + functionCallback + ")\">确定</button><button class='btn btn-default' id='btnShowMessageCancel' onclick=\"$.hideModalConfirmDialog()\" >取消</button></div></div></div></div></div>");
        }

        //div.messageBox = $("<div id=\"divConfirmDialog\" class=\"c_mask\"><h3><a class=\"delete\" href=\"javascript:void(0);\" onclick=\"$.hideConfirmDialog()\">×</a>提示</h3><div class=\"c_mask_bd\"><div class=\"c_alert3\"><span class=\"ico_alert\"></span><p class=\"single\">" + msg + "</p><br /></div><div style=\"text-align:center;\"><input id=\"btnShowConfirm\" type=\"button\" class=\"btn btn-primary ng-binding\" value=\"确 定\" onclick=\"$.sureConfirmDialog(" + functionCallback + ")\" />&nbsp;<input id=\"btnCancelConfirm\" type=\"button\" class=\"btn btn-primary ng-binding\" value=\"取 消\" style=\"margin-left:10px\" onclick=\"$.hideConfirmDialog()\" /></div></div></div>")
        //    .css({
        //        "width": widthstr == null ? 300 : widthstr,
        //        "height": heightstr == null ? 180 : heightstr
        //    });


        div.show();

        $("#divConfirmDialog").focus();

        if (!disableautohide) {
            $(document).keyup(function (event) {
                if (event.keyCode == 13) {
                    $.hideModalConfirmDialog();
                }
            });
        }
    }

    //确定按钮事件
    $.sureModalConfirmDialog = function (functionCallback) {
        if (this.objStr != null) {
            functionCallback(this.objStr);
        } else {
            functionCallback();
        }
        $('#divConfirmDialog').modal('hide');

    }

    //隐藏Dialog
    $.hideModalConfirmDialog = function () {
        $('#divConfirmDialog').modal('hide');
    }

    $.showMessageBox = function (msg, url, widthstr) {
        this.hrefurl = url;
        var div = {
            show: function () {
                if ($(".messageBoxMask").length) {
                    var newwidth = document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width();
                    newwidth = newwidth + $(document).scrollLeft();
                    $(".messageBoxMask").css({ width: newwidth + 'px', height: $(document).height() + 'px' });
                    $(".messageBoxMask").show();
                } else {
                    $(document.body).append(div.mask);
                }
                if ($("#divMessageBox").length) {
                    $("#divMessageBox").remove();
                    $(document.body).append(div.messageBox);
                } else {
                    $(document.body).append(div.messageBox);
                }

                var top = 0;
                if ($(window).scrollTop() > 0) {
                    top = $(window).height() + $(window).scrollTop() - ($(window).height() + div.messageBox.height()) / 2;
                } else {
                    top = ($(window).height() - div.messageBox.height()) / 2
                }

                div.messageBox.css({
                    "position": "absolute",
                    "left": ($(document.body).width() - 300) / 2,
                    "top": top,
                    "z-index": 1200
                }).show();
            }
        };
        div.mask = $("<div class='messageBoxMask' id='messageBoxMask'></div>")
           .css({
               "background-Color": "rgb(255, 255, 255)",
               "position": "absolute",
               "border": "medium none",
               "left": 0,
               "right": 0,
               "top": 0,
               "bottom": 0,
               "-moz-opacity": 0.4,
               "opacity": 0.4,
               "filter": "alpha(opacity=40)",
               "z-index": 1100,
               "width": (document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width()) + $(document).scrollLeft(),
               "height": $(window).height() > $(document.body).height() ? $(window).height() : $(document.body).height()
           });
        if (widthstr == null) {
            div.messageBox = $("<div id=\"divMessageBox\" class=\"c_mask\"><h3><a class=\"delete\" href=\"javascript:void(0);\" onclick=\"$.hideMessageBox()\">×</a>提示</h3><div class=\"c_mask_bd\"><div class=\"c_alert3\"><span class=\"ico_alert\"></span><p class=\"single\">" + msg + "</p><br /></div><input id=\"btnShowMessage\" type=\"button\" class=\"btn btn-primary ng-binding\" value=\"确 定\" style=\"margin-left:80px\" onclick=\"$.hideMessageBox()\" /></div></div>")
            .css({
                "width": "300px"
            });
        }
        else {
            div.messageBox = $("<div id=\"divMessageBox\" class=\"c_mask\"><h3><a class=\"delete\" href=\"javascript:void(0);\" onclick=\"$.hideMessageBox()\">×</a>提示</h3><div class=\"c_mask_bd\"><div class=\"c_alert3\"><span class=\"ico_alert\"></span><p class=\"single\">" + msg + "</p><br /></div><input id=\"btnShowMessage\" type=\"button\" class=\"btn btn-primary ng-binding\" value=\"确 定\" style=\"position: absolute; left: 0; top: 0; right: 0; bottom: -140; margin: auto\" onclick=\"$.hideMessageBox()\" /></div></div>")
            .css({
                "width": widthstr + "px"
            });
        }

        div.show();
        MaskCenter($("#messageBoxMask"));
        center($("#divMessageBox"));
        $("#btnShowMessage").focus();
        $(document).keyup(function (event) {
            if (event.keyCode == 13) {
                $.hideMessageBox();
            }
        });
    }

    $.hideMessageBox = function () {
        if ($(".messageBoxMask").length) {
            //setTimeout(function () { $(".loadingDiv").hide(); $("#divProcessingBar").hide(); }, 500);
            $(".messageBoxMask").hide();
            $("#divMessageBox").hide();
            if (this.hrefurl != null) { location.href = this.hrefurl; }
        }
    }
    //弹出提示框带有回调函数FN
    $.showCallbackMessageBox = function (msg, callbackfn, obj) {
        this.objCallbackStr = obj;
        var div = {
            show: function () {
                if ($(".messageBoxMask").length) {
                    var newwidth = document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width();
                    newwidth = newwidth + $(document).scrollLeft();
                    $(".messageBoxMask").css({ width: newwidth + 'px', height: $(document).height() + 'px' });
                    $(".messageBoxMask").show();
                } else {
                    $(document.body).append(div.mask);
                }
                if ($("#divMessageBox").length) {
                    $("#divMessageBox").remove();
                    $(document.body).append(div.messageBox);
                } else {
                    $(document.body).append(div.messageBox);
                }

                var top = 0;
                if ($(window).scrollTop() > 0) {
                    top = $(window).height() + $(window).scrollTop() - ($(window).height() + div.messageBox.height()) / 2;
                } else {
                    top = ($(window).height() - div.messageBox.height()) / 2
                }

                div.messageBox.css({
                    "position": "absolute",
                    "left": ($(document.body).width() - 300) / 2,
                    "top": top,
                    "z-index": 1200
                }).show();
            }
        };
        div.mask = $("<div class='messageBoxMask' id='messageBoxMask'></div>")
           .css({
               "background-Color": "rgb(255, 255, 255)",
               "position": "absolute",
               "border": "medium none",
               "left": 0,
               "right": 0,
               "top": 0,
               "bottom": 0,
               "-moz-opacity": 0.4,
               "opacity": 0.4,
               "filter": "alpha(opacity=40)",
               "z-index": 1100,
               "width": (document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width()) + $(document).scrollLeft(),
               "height": $(window).height() > $(document.body).height() ? $(window).height() : $(document.body).height()
           });
        div.messageBox = $("<div id=\"divMessageBox\" class=\"c_mask\"><h3><a class=\"delete\" href=\"javascript:void(0);\" onclick=\"$.hideMessageBox()\">×</a>提示</h3><div class=\"c_mask_bd\"><div class=\"c_alert3\"><span class=\"ico_alert\"></span><p class=\"single\">" + msg + "</p><br /></div><input id=\"btnShowMessage\" type=\"button\" class=\"btn btn_azure\" value=\"确 定\" style=\"margin-left:80px\" onclick=\"$.sureCallbackbtn(" + callbackfn + ")\" /></div></div>")
            .css({
                "width": "300px"
            });
        div.show();
        MaskCenter($("#messageBoxMask"));
        center($("#divMessageBox"));
        $("#btnShowMessage").focus();
        $(document).keyup(function (event) {
            if (event.keyCode == 13) {
                $.hideMessageBox();
            }
        });
    }
    //弹出提示框回调函数
    $.sureCallbackbtn = function (functionCallback) {
        if ($(".messageBoxMask").length) {
            $(".messageBoxMask").hide();
            $("#divMessageBox").hide();
            if (this.objCallbackStr != null) {
                functionCallback(this.objCallbackStr);
            }
            else {
                functionCallback();
            }
        }
    }
    //弹出confirm优化页面start
    //msg 提示消息文字(不为空)
    //functionCallback 回调function(不为空)
    //heightstr 提示框高度(可为空)
    //widthstr 提示框宽度(可为空)
    //obj 回调function(obj)的参数(可为空)
    $.showConfirmDialog = function (msg, functionCallback, obj, heightstr, widthstr) {
        this.objStr = obj;
        var div = {
            show: function () {
                if ($(".confirmDialogMask").length) {
                    var newwidth = document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width();
                    newwidth = newwidth + $(document).scrollLeft();
                    $(".confirmDialogMask").css({ width: newwidth + 'px', height: $(document).height() + 'px' });
                    $(".confirmDialogMask").show();
                } else {
                    $(document.body).append(div.mask);
                }
                if ($("#divConfirmDialog").length) {
                    $("#divConfirmDialog").remove();
                    $(document.body).append(div.messageBox);
                } else {
                    $(document.body).append(div.messageBox);
                }

                var top = 0;
                if ($(window).scrollTop() > 0) {
                    top = $(window).height() + $(window).scrollTop() - ($(window).height() + div.messageBox.height()) / 2;
                } else {
                    top = ($(window).height() - div.messageBox.height()) / 2
                }

                div.messageBox.css({
                    "position": "absolute",
                    "left": ($(document.body).width() - 300) / 2,
                    "top": top,
                    "z-index": 1200
                }).show();
            }
        };
        div.mask = $("<div class='confirmDialogMask' id='confirmDialogMask'></div>")
           .css({
               "background-Color": "rgb(255, 255, 255)",
               "position": "absolute",
               "border": "medium none",
               "left": 0,
               "right": 0,
               "top": 0,
               "bottom": 0,
               "-moz-opacity": 0.4,
               "opacity": 0.4,
               "filter": "alpha(opacity=40)",
               "z-index": 1100,
               "width": (document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width()) + $(document).scrollLeft(),
               "height": $(window).height() > $(document.body).height() ? $(window).height() : $(document.body).height()
           });
        div.messageBox = $("<div id=\"divConfirmDialog\" class=\"c_mask\"><h3><a class=\"delete\" href=\"javascript:void(0);\" onclick=\"$.hideConfirmDialog()\">×</a>提示</h3><div class=\"c_mask_bd\"><div class=\"c_alert3\"><span class=\"ico_alert\"></span><p class=\"single\">" + msg + "</p><br /></div><div style=\"text-align:center;\"><input id=\"btnShowConfirm\" type=\"button\" class=\"btn btn-primary ng-binding\" value=\"确 定\" onclick=\"$.sureConfirmDialog(" + functionCallback + ")\" />&nbsp;<input id=\"btnCancelConfirm\" type=\"button\" class=\"btn btn-primary ng-binding\" value=\"取 消\" style=\"margin-left:10px\" onclick=\"$.hideConfirmDialog()\" /></div></div></div>")
            .css({
                "width": widthstr == null ? 300 : widthstr,
                "height": heightstr == null ? 180 : heightstr
            });
        div.show();
        MaskCenter($("#confirmDialogMask"));
        center($("#divConfirmDialog"));
        $("#divConfirmDialog").focus();
        $(document).keyup(function (event) {
            if (event.keyCode == 13) {
                $.hideMessageBox();
            }
        });
    }
    //确定按钮事件
    $.sureConfirmDialog = function (functionCallback) {
        if ($(".confirmDialogMask").length) {
            $(".confirmDialogMask").hide();
            $("#divConfirmDialog").hide();
            if (this.objStr != null) {
                functionCallback(this.objStr);
            }
            else {
                functionCallback();
            }
        }
    }
    //隐藏Dialog
    $.hideConfirmDialog = function () {
        if ($(".confirmDialogMask").length) {
            $(".confirmDialogMask").hide();
            $("#divConfirmDialog").hide();
        }
    }
    //弹出confirm优化页面end

    //关闭弹出层
    $.closeWin = function (srcElem, p) {
        if ($(".coverlay").length) $(".coverlay").hide();
        srcElem.hide();
    }

    //弹出层
    $.showWin = function (srcElem, p) {
        var g = {
            setting: {},
            show: function () {
                if ($(".coverlay").length) {
                    var newwidth = document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width();
                    newwidth = newwidth + $(document).scrollLeft();
                    $(".coverlay").css({ width: newwidth + 'px', height: $(document).height() + 'px' });
                    $(".coverlay").show();
                }
                else {
                    $(document.body).append(g.mask);
                }

                var top = 0;
                if ($(window).scrollTop() > 0) {
                    top = $(window).height() + $(window).scrollTop() - ($(window).height() + g.src.height()) / 2;
                } else {
                    top = ($(window).height() - g.src.height()) / 2
                }

                g.src.css({
                    "position": "absolute",
                    "left": ($(document.body).width() - g.src.width()) / 2,
                    "top": top,
                    "z-index": 1000
                }).show();
            },
            close: function () {
                if ($(".coverlay").length) $(".coverlay").hide();
                g.src.hide();
            }
        };
        g.mask = $("<div class='coverlay' id='coverlay'/>")
           .css({
               "background-Color": "rgb(255, 255, 255)",
               "position": "absolute",
               "border": "medium none",
               "left": 0,
               "right": 0,
               "top": 0,
               "bottom": 0,
               "-moz-opacity": 0.4,
               "opacity": 0.4,
               "filter": "alpha(opacity=40)",
               "z-index": 99,
               "width": (document.body.scrollWidth > $(document.body).width() ? document.body.scrollWidth : $(document.body).width()) + $(document).scrollLeft(),
               "height": $(window).height() > $(document.body).height() ? $(window).height() : $(document.body).height()
           });
        g.setting = p || {
            containerId: "tuna_jmpinfo"
        };

        g.src = srcElem;
        MaskCenter($("#coverlay"));
        g.show();

        return g;
    };

    //鼠标提示框
    $.fn.extend({
        cTips: function (p) {
            return $.addTips($(this), p);
        }
    });

    //弹出层
    $.fn.extend({
        cPopWin: function (p) {
            return $.showWin($(this), p);
        }
    });
    //弹出层
    $.fn.extend({
        openWin: function (p) {
            return $.showWin($(this), p);
        }
    });

    //关闭弹出层
    $.fn.extend({
        closeWin: function (p) {
            return $.closeWin($(this), p);
        }
    });

    //验证是否为手机格式
    $.fn.extend({
        isMobile: function () {
            var isMobile = /^1(3|5|8)[0-9]{9}$/
            return isMobile.test($(this).val());
        }
    });

    //验证是否为整数
    $.fn.extend({
        isInt: function () {
            var isInt = /^\+?[0-9][0-9]*$/
            return isInt.test($(this).val());
        }
    });

    //验证是否为金额
    //$.fn.extend({
    //    isMoney: function () {
    //        var isMoney = /^[0-9]*(\.[0-9]{1,2})?$/
    //        return isMoney.test($(this).val());
    //    }
    //});

    //验证是否为金额
    $.fn.extend({
        isMoney: function () {
            var isMoney = /^(\-?)[0-9]*(\.[0-9]{1,2})?$/
            return isMoney.test($(this).val());
        }
    });

    

    //验证是否为邮箱格式
    $.fn.extend({
        isEmail: function () {
            var isEmail = /^\w+((-\w+)|(\.\w+))*\@[A-Za-z0-9]+((\.|-)[A-Za-z0-9]+)*\.[A-Za-z0-9]+$/
            return isEmail.test($(this).val());
        }
    });

    //验证是否为时间格式：hh:mm 
    $.fn.extend({
        isTimehm: function () {
            var isTimehm = /^(0\d{1}|1\d{1}|2[0-3]):([0-5]\d{1})$/
            return isTimehm.test($(this).val());
        }
    });

    $.fn.extend({
        isTextTooLong: function (Length) {
            return $(this).val().length > Length;
        }
    });

    $.fn.extend({
        getPageControlPoint: function (controlPointName, productCatagoryId, productPatternId, productSaleMode) {
            if (productCatagoryId == null || productPatternId == null || controlPointName == null) {
                return "productPatternId,productCatagoryId 不能为空";
            }

            //页面关闭前一直优先读取缓存
            var allctrl = $('.tab_box').data("pageControl");

            if (allctrl == null) {
                if ($('.tab_box') == null) {
                    return "次函数只能在6381中使用";
                }

                $.ajax({
                    type: 'GET',
                    url: AP_ROOT + '/Product/Shared/GetHiddenControl',
                    contentType: "application/json; charset=utf-8",
                    dataType: 'json',
                    success: function (data) {
                        $('.tab_box').data("pageControl", data);

                    },
                    error: function (data) {
                        //alert(data.responseText);
                    },
                    async: false
                });
                allctrl = $('.tab_box').data("pageControl");
            }

            if (allctrl == null) return null;
            var result = "";

            $.each(allctrl, function (index, ele) {
                if (ele['ControlPointName'] == controlPointName) {
                    var patternList = ele['ProductPatternIDList'].split(',');
                    var catagoryList = ele['ProductCatagoryIDList'].split(',');
                    var saleModeList = null;
                    if (ele['SaleMode'] == null) {
                        saleModeList = null;
                    } else {
                        saleModeList = ele['SaleMode'].split(',');
                    }
                    var returnVal = ele['ReturnValue'];

                    if (($.inArray(productPatternId, patternList) > -1 || $.inArray('-1', patternList) > -1)
                        && ($.inArray(productCatagoryId, catagoryList) > -1 || $.inArray('-1', catagoryList) > -1)
                        && (saleModeList == null || $.inArray(productSaleMode, saleModeList) > -1)) {
                        if (returnVal != null) {
                            result = returnVal;
                            //相当于break；
                            return false;
                        } else {
                            result = "true";
                            //相当于break；
                            return false;
                        }
                    }
                }
            });

            if (result == "true") return true;
            if (result == "") return false;
            return result;
        }
    });

    //将表单转换成Json对象
    $.fn.serializeObject = function () {
        var o = {};
        var a = this.serializeArray();
        $.each(a, function () {
            if (o[this.name]) {
                if (!o[this.name].push) {
                    o[this.name] = [o[this.name]];
                }
                if (this.value != '') {
                    o[this.name].push(this.value || '');
                }
            } else {
                if (this.value != '') {
                    o[this.name] = this.value || '';
                }
            }
        });
        return o;
    }

    //Table添加TR数据
    $.fn.extend({
        addRow: function (args) {
            var tr = null;
            $(this).find("tr").each(function () {
                if ($(this).css("display") == "none") {
                    tr = $(this).clone().show();
                }
            });
            for (i = 1; i <= arguments.length; i++) {
                tr.children("td:nth-child(" + i + ")").html(arguments[i - 1]);
            }
            $(this).append(tr);
            return tr;
        }
    });
    //Table清楚TR数据
    $.fn.extend({
        clearRow: function () {
            var trlist = $(this).find("tr");
            for (i = 1; i < trlist.length; i++) {
                if ($(trlist[i]).css("display") != "none") {
                    $(trlist[i]).remove();
                }
            }
        }
    });
    $.fn.extend({
        clearAll: function () {
            var trlist = $(this).find("tr");
            for (i = 1; i < trlist.length; i++) {
                $(trlist[i]).remove();
            }
        }
    });
    //Table获取Json对象
    $.fn.extend({
        getJson: function (jsonObj, cn) {
            var trlist = $(this).find("tr");
            var temp = "jsonObj." + cn + "=[]";
            eval(temp);

            for (i = 2; i < trlist.length; i++) {
                temp = "";
                $(trlist[i]).find("input").each(function (i, e) {
                    if (i == 0 && $(e).attr("type") == "checkbox" && !$(e).attr("checked")) {
                        return false;
                    }
                    if (i == 0 && $(e).attr("type") == "checkbox") {
                    }
                    else {
                        if ($(e).attr("name") != "" && $(e).val() != "") {
                            temp += $(e).attr("name") + ":" + $(e).val() + ",";
                        }
                    }
                });
                if (temp != "") {
                    temp = "jsonObj." + cn + ".push({" + temp.substring(0, temp.length - 1) + "});";
                    eval(temp);
                }
            }
        }
    });

    //序列化table中的所有控件，现包括text,hidden,checkbox,select
    $.fn.extend({
        serializeTable: function(jsonObj, jsonName) {
            eval("jsonObj." + jsonName + "=[]");

            var trList = $(this).find("tr");
            for (i = 0; i < trList.length; i++) {
                var evalString = "";
                $(trList[i]).find("input").each(function(i, e) {
                    if ($(e).attr("name")) {
                        if ($(e).attr("type") && $(e).attr("type") == "text") {
                            evalString += "'" + $(e).attr("name") + "':'" + $(e).val() + "',";
                        } else if ($(e).attr("type") && $(e).attr("type") == "hidden") {
                            evalString += "'" + $(e).attr("name") + "':'" + $(e).val() + "',";
                        } else if ($(e).attr("type") && $(e).attr("type") == "checkbox") {
                            evalString += "'" + $(e).attr("name") + "':" + ($(e).attr("checked") ? "true" : "false") + ",";
                        } else if ($(e).attr("type") && $(e).attr("type") == "radio") {
                        }
                    }
                });
                $(trList[i]).find("select").each(function(i, e) {
                    if ($(e).attr("name")) {
                        evalString += "'" + $(e).attr("name") + "':'" + $(e).val() + "',";
                    }
                });

                if (evalString) {
                    //evalString = evalString.replace(/\[/g, "\\[").replace(/\]/g, "\\]");
                    evalString = "jsonObj." + jsonName + ".push({" + evalString.substring(0, evalString.length - 1) + "});";
                    eval(evalString);
                }

            }
        }
    });

    String.prototype.trimEnd = function (trimStr) {
        if (!trimStr) { return this; }
        var temp = this;
        while (true) {
            if (temp.substr(temp.length - trimStr.length, trimStr.length) != trimStr) {
                break;
            }
            temp = temp.substr(0, temp.length - trimStr.length);
        }
        return temp;
    };

    Date.prototype.add = function (milliseconds) {

        var m = this.getTime() + milliseconds;
        var d = new Date(m);
        return new Date(m);
    };
    Date.prototype.addSeconds = function (second) {
        return this.add(second * 1000);
    };
    Date.prototype.addMinutes = function (minute) {
        return this.addSeconds(minute * 60);
    };
    Date.prototype.addHours = function (hour) {
        return this.addMinutes(60 * hour);
    };

    Date.prototype.addDays = function (day) {
        return this.addHours(day * 24);
    };

    Date.isLeepYear = function (year) {
        return (year % 4 == 0 && year % 100 != 0)
    };

    Date.daysInMonth = function (year, month) {
        if (month == 2) {
            if (year % 4 == 0 && year % 100 != 0)
                return 29;
            else
                return 28;
        }
        else if ((month <= 7 && month % 2 == 1) || (month > 7 && month % 2 == 0))
            return 31;
        else
            return 30;
    };

    Date.prototype.addMonth = function () {
        var m = this.getMonth();
        if (m == 12) return new Date(this.getFullYear() + 1, 1, this.getDate(), this.getHours(), this.getMinutes(), this.getSeconds());
        var daysInNextMonth = Date.daysInMonth(this.getFullYear(), this.getMonth() + 1);
        var day = this.getDate();
        if (day > daysInNextMonth) {
            day = daysInNextMonth;
        }
         
        return new Date(this.getFullYear(), this.getMonth() + 1, day, this.getHours(), this.getMinutes(), this.getSeconds());
    };

    Date.prototype.subMonth = function () {
        var m = this.getMonth();
        if (m == 0) return new Date(this.getFullYear() - 1, 12, this.getDate(), this.getHours(), this.getMinutes(), this.getSeconds());
        var day = this.getDate();
        var daysInPreviousMonth = Date.daysInMonth(this.getFullYear(), this.getMonth());
        if (day > daysInPreviousMonth) {
            day = daysInPreviousMonth;
        }
        return new Date(this.getFullYear(), this.getMonth() - 1, day, this.getHours(), this.getMinutes(), this.getSeconds());
    };

    Date.prototype.addMonths = function (addMonth) {
        var result = this;
        if (addMonth > 0) {
            while (addMonth > 0) {
                result = result.addMonth();
                addMonth--;
            }
        } else if (addMonth < 0) {
            while (addMonth < 0) {
                result = result.subMonth();
                addMonth++;
            }
        } else {
            result = this;
        }
        return result;
    };

    Date.prototype.addYears = function (year) {
        return new Date(this.getFullYear() + year, this.getMonth(), this.getDate(), this.getHours(), this.getMinutes(), this.getSeconds());
    };

    Date.prototype.Format = function (fmt) { //author: meizz 
        var o = {
            "M+": this.getMonth() + 1, //月份 
            "d+": this.getDate(), //日 
            "h+": this.getHours(), //小时 
            "m+": this.getMinutes(), //分 
            "s+": this.getSeconds(), //秒 
            "q+": Math.floor((this.getMonth() + 3) / 3), //季度 
            "S": this.getMilliseconds() //毫秒 
        };
        if (/(y+)/.test(fmt)) fmt = fmt.replace(RegExp.$1, (this.getFullYear() + "").substr(4 - RegExp.$1.length));
        for (var k in o)
            if (new RegExp("(" + k + ")").test(fmt)) fmt = fmt.replace(RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
        return fmt;
    }

    //封装Checkbox的操作
    $.checkbox = {
        //全选，n:Name
        all: function (n) {
            $("input[name=" + n + "]").each(
                function () { $(this).prop("checked", "checked"); }
            );
        },
        //全不选，n:Name
        not: function (n) {
            $("input[name=" + n + "]").each(
                function () { $(this).prop("checked",''); }
            );
        },
        //反选，n:Name
        or: function (n) {
            $("input[name=" + n + "]").each(
            function () {
                if ($(this).attr("checked")) {
                    $(this).removeAttr("checked");
                } else { $(this).attr("checked", "checked"); }
            });
        },

        //选中个数，n:Name
        selcount: function (n) {
            return $("input[name=" + n + "]:checked").length;
        },

        //获取Value数组
        vals: function (n) {
            var vals = [];
            $("input[name=" + n + "]:checked").each(
                function (i) { vals[i] = $(this).val(); }
            );
            return vals;
        }
    };

    //封装Radio的操作
    $.radio = {
        val: function (n) {
            return $("input[name=" + n + "]:checked").val();
        },
        init: function () {
            $("input[type=radio]").each(function () {

                $("input[name='" + $(this).attr("name") + "']").each(function (i, e) {
                    if ($(e).attr("type") == "radio" && $(e).attr("checked")) {
                        $(this).parent().addClass("o_label_cur");
                    } else {
                        $(this).parent().removeClass("o_label_cur");
                    }
                });

                $(this).click(function () {
                    $("input[name='" + $(this).attr("name") + "']").each(function (i, e) {
                        if ($(e).attr("type") == "radio") {
                            $(this).parent().removeClass("o_label_cur");
                        }
                    });
                    $(this).parent().addClass("o_label_cur");
                });
            });
        }
    };

    $.calendar = {
        load: function (data, left, right, isapprove, func) {
            var html = '<div class="reserve_box">';
            html += '<ul class="reserve_datebox layoutfix">';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.PrevCalendarMonth.Year + ',' + data.PrevCalendarMonth.Month + ');" class="back"></a><span class="year">' + data.CurrCalendarMonth.Year + '年</span></li>';
            html += '<li class="current">' + data.CurrCalendarMonth.Month + '月</li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[1].Year + ',' + data.CalendarMonth[1].Month + ');">' + data.CalendarMonth[1].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[2].Year + ',' + data.CalendarMonth[2].Month + ');">' + data.CalendarMonth[2].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[3].Year + ',' + data.CalendarMonth[3].Month + ');">' + data.CalendarMonth[3].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[4].Year + ',' + data.CalendarMonth[4].Month + ');">' + data.CalendarMonth[4].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[5].Year + ',' + data.CalendarMonth[5].Month + ');">' + data.CalendarMonth[5].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.NextCalendarMonth.Year + ',' + data.NextCalendarMonth.Month + ');" class="go"></a></li>';
            html += '</ul>'
            html += '</div>'
            html += '<div class="basefix">';
            html += '<div class="reserve_record">';
            for (i = 0; i < data.CalendarWeek.length; i++) {
                html += '<dl>';
                if (i == 0) {
                    html += '<dt class="month"><span>' + data.CurrCalendarMonth.Month + '</span>月</dt>';
                } else {
                    html += '<dt></dt>';
                }
                //获取当前周状态列表
                var ItemStatus = this.getStatus(data, i);
                //设置左边列框
                if (ItemStatus.length > 0) {
                    for (k = 0; k < ItemStatus.length; k++) {
                        for (j = 0; j < data.CalendarCatetory.length; j++) {
                            html += '<dd>' + data.CalendarCatetory[j].Name + '</dd>';
                        }
                    }
                } else {
                    html += '<dd></dd>';
                }
                html += '</dl>';
            }
            html += '</div>';
            html += '<table width="100%" class="reserve_table">';
            html += '<thead>';
            html += '<tr>';
            html += '<th style="width:90px;">星期日</th>';
            html += '<th style="width:90px;">星期一</th>';
            html += '<th style="width:90px;">星期二</th>';
            html += '<th style="width:90px;">星期三</th>';
            html += '<th style="width:90px;">星期四</th>';
            html += '<th style="width:90px;">星期五</th>';
            html += '<th style="width:90px;">星期六</th>';
            html += '</tr>';
            html += '</thead>';
            html += '<tbody>';
            for (i = 0; i < data.CalendarWeek.length; i++) {
                html += "<tr>";
                for (j = 0; j < data.CalendarWeek[i].CalendarDate.length; j++) {
                    //判断当前周是否存在数据和数据审核状态

                    //获取当前周状态列表
                    var ItemStatus = this.getStatus(data, i);

                    //设置弹出框或自定义事件
                    if (func != null) {
                        html += "<td>";
                    }
                    else {
                        if (data.CalendarWeek[i].CalendarDate[j].Data.length > 0) {
                            html += "<td onclick='calendarClick(" + data.CalendarWeek[i].CalendarDate[j].Year + "," + data.CalendarWeek[i].CalendarDate[j].Month + "," + data.CalendarWeek[i].CalendarDate[j].Day + ")'>";
                        } else {
                            html += "<td>";
                        }
                    }
                    //设置年月栏
                    if (data.CalendarWeek[i].CalendarDate[j].Month != data.CurrCalendarMonth.Month) {
                        html += '<p class="day">' + data.CalendarWeek[i].CalendarDate[j].Month + '/' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                    } else {
                        html += '<p class="day">' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                    }
                    //存在数据
                    if (ItemStatus.length > 0) {
                        switch (ItemStatus.length) {
                            case 1:
                                html += this.setHtml(data, i, j, left, right, isapprove, func, ItemStatus);
                                break;
                            case 2:
                                html += this.setHtml(data, i, j, left, right, isapprove, func, ItemStatus);
                                break;
                        }
                    } else {
                        html += '<p class="none_border"></p>';
                    }
                    html += '</td>';
                }
                html += "</tr>"
            }
            html += '</tbody>';
            html += '</table>';
            html += '</div>';
            if (isapprove != null && isapprove) {
                html += '<div class="reserve_state">审核状态：<span class="pas">通过</span><span class="audit">待审核</span><span class="refuse">拒绝</span></div>';
            }
            return html;
        },
        loadSchedule: function (data) {
            var currentDate = new Date();

            var html = '<div class="reserve_box">';
            html += '<ul class="reserve_datebox layoutfix">';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.PrevCalendarMonth.Year + ',' + data.PrevCalendarMonth.Month + ');" class="back"></a><span class="year">' + data.CurrCalendarMonth.Year + '年</span></li>';
            html += '<li class="current">' + data.CurrCalendarMonth.Month + '月</li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[1].Year + ',' + data.CalendarMonth[1].Month + ');">' + data.CalendarMonth[1].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[2].Year + ',' + data.CalendarMonth[2].Month + ');">' + data.CalendarMonth[2].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[3].Year + ',' + data.CalendarMonth[3].Month + ');">' + data.CalendarMonth[3].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[4].Year + ',' + data.CalendarMonth[4].Month + ');">' + data.CalendarMonth[4].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[5].Year + ',' + data.CalendarMonth[5].Month + ');">' + data.CalendarMonth[5].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.NextCalendarMonth.Year + ',' + data.NextCalendarMonth.Month + ');" class="go"></a></li>';
            html += '</ul>'
            html += '</div>'
            html += '<div class="basefix schedule_date">';
            html += '<div class="reserve_record">';
            for (i = 0; i < data.CalendarWeek.length; i++) {
                html += '<dl>';
                if (i == 0) {
                    html += '<dt class="month"><span>' + data.CurrCalendarMonth.Month + '</span>月</dt>';
                } else {
                    html += '<dt></dt>';
                }
                //获取当前周状态列表
                html += '<dd></dd>';
                html += '</dl>';
            }
            html += '</div>';
            html += '<table width="100%" class="reserve_table">';
            html += '<thead>';
            html += '<tr>';
            html += '<th style="width:90px;">星期日</th>';
            html += '<th style="width:90px;">星期一</th>';
            html += '<th style="width:90px;">星期二</th>';
            html += '<th style="width:90px;">星期三</th>';
            html += '<th style="width:90px;">星期四</th>';
            html += '<th style="width:90px;">星期五</th>';
            html += '<th style="width:90px;">星期六</th>';
            html += '</tr>';
            html += '</thead>';
            html += '<tbody>';
            for (i = 0; i < data.CalendarWeek.length; i++) {
                html += "<tr>";
                for (j = 0; j < data.CalendarWeek[i].CalendarDate.length; j++) {
                    html += "<td>";
                    //设置年月栏
                    if (data.CalendarWeek[i].CalendarDate[j].Month != data.CurrCalendarMonth.Month) {
                        html += '<p class="day">' + data.CalendarWeek[i].CalendarDate[j].Month + '/' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                    } else {
                        if ((currentDate.getFullYear() < data.CalendarWeek[i].CalendarDate[j].Year) ||
                            ((currentDate.getFullYear() == data.CalendarWeek[i].CalendarDate[j].Year) && (currentDate.getMonth() + 1) < data.CalendarWeek[i].CalendarDate[j].Month) ||
                            ((currentDate.getFullYear() == data.CalendarWeek[i].CalendarDate[j].Year) && (currentDate.getMonth() + 1) == data.CalendarWeek[i].CalendarDate[j].Month) && (currentDate.getDate() <= data.CalendarWeek[i].CalendarDate[j].Day)) {
                            if (data.CalendarWeek[i].CalendarDate[j].Data.length > 0) {
                                html += '<p class="day closeday"><a href="javascript:openSchedule(' + data.CalendarWeek[i].CalendarDate[j].Year + ',' + data.CalendarWeek[i].CalendarDate[j].Month + ',' + data.CalendarWeek[i].CalendarDate[j].Day + ');" class="btn btn_azure_ss">打开</a>' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                            }
                            else {
                                html += '<p class="day goday"><a href="javascript:closeSchedule(' + data.CalendarWeek[i].CalendarDate[j].Year + ',' + data.CalendarWeek[i].CalendarDate[j].Month + ',' + data.CalendarWeek[i].CalendarDate[j].Day + ');" class="btn btn_s">关闭</a>' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                            }
                        }
                        else {
                            html += '<p class="day closeday">' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                        }
                    }
                    if (data.CalendarWeek[i].CalendarDate[j].Data.length > 0) {
                        html += '<p class="none_border closedate">关闭</p>';
                    } else {
                        html += '<p class="none_border">出发</p>';
                    }
                    html += '</td>';
                }
                html += "</tr>"
            }
            html += '</tbody>';
            html += '</table>';
            html += '</div>';
            return html;
        },
        //多行程展示班期。
        loadForTrip: function (data, scheduledata, TourInfoID) {
            var currentDate = new Date();
            var html = '<div class="reserve_box" style="width:335px;margin-top:0px;background:#F0FAFF;margin-left:-1px">';
            html += '<ul class="reserve_datebox layoutfix" style="width:250px;left:70px">';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + TourInfoID + ',' + data.PrevCalendarMonth.Year + ',' + data.PrevCalendarMonth.Month + ');" class="back"></a><span class="year">' + data.CurrCalendarMonth.Year + '年</span></li>';
            html += '<li class="current">' + data.CurrCalendarMonth.Month + '月</li>';
            //html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[1].Year + ',' + data.CalendarMonth[1].Month + ');">' + data.CalendarMonth[1].Month + '月</a></li>';
            //html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[2].Year + ',' + data.CalendarMonth[2].Month + ');">' + data.CalendarMonth[2].Month + '月</a></li>';
            //html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[3].Year + ',' + data.CalendarMonth[3].Month + ');">' + data.CalendarMonth[3].Month + '月</a></li>';
            //html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[4].Year + ',' + data.CalendarMonth[4].Month + ');">' + data.CalendarMonth[4].Month + '月</a></li>';
            //html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + data.CalendarMonth[5].Year + ',' + data.CalendarMonth[5].Month + ');">' + data.CalendarMonth[5].Month + '月</a></li>';
            html += '<li><a href="javascript:void(0)" onclick="loadCalendar(' + TourInfoID + ',' + data.NextCalendarMonth.Year + ',' + data.NextCalendarMonth.Month + ');" class="go"></a></li>';
            html += '</ul>'
            html += '</div>'
            html += '<div class="basefix schedule_date"  style=" position: relative;right: -0.5px;">';

            html += '<table style="width:350px" class="reserve_table">';
            html += '<thead>';
            html += '<tr>';
            html += '<th style="width:50px;">日</th>';
            html += '<th style="width:50px;">一</th>';
            html += '<th style="width:50px;">二</th>';
            html += '<th style="width:50px;">三</th>';
            html += '<th style="width:50px;">四</th>';
            html += '<th style="width:50px;">五</th>';
            html += '<th style="width:50px;">六</th>';
            html += '</tr>';
            html += '</thead>';
            html += '<tbody>';
            for (i = 0; i < data.CalendarWeek.length; i++) {
                html += "<tr>";
                for (j = 0; j < data.CalendarWeek[i].CalendarDate.length; j++) {
                    html += "<td>";
                    //设置年月栏

                    var scheduledstyle = "";
                    var b = scheduledata.split(",");
                    for (var m = 0; m < b.length; m++) {
                        if (data.CalendarWeek[i].CalendarDate[j].Year == b[m].split('-')[0] && data.CalendarWeek[i].CalendarDate[j].Month == b[m].split('-')[1] && data.CalendarWeek[i].CalendarDate[j].Day == b[m].split('-')[2]) {
                            scheduledstyle = "style=\"background-color:yellow\"";
                        }
                    }
                    //html += '<p ' + scheduledstyle + ' class="day closeday">' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                    if (data.CalendarWeek[i].CalendarDate[j].Month != data.CurrCalendarMonth.Month) {
                        html += '<p ' + scheduledstyle + ' class="day">' + data.CalendarWeek[i].CalendarDate[j].Month + '/' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                    } else {
                        html += '<p ' + scheduledstyle + ' class="day closeday">' + data.CalendarWeek[i].CalendarDate[j].Day + '</p>';
                    }
                    /*if (data.CalendarWeek[i].CalendarDate[j].Data.length > 0) {
                        html += '<p class="none_border closedate">关闭</p>';
                    } else {
                        html += '<p class="none_border">出发</p>';
                    }*/
                    html += '</td>';
                }
                html += "</tr>"
            }
            html += '</tbody>';
            html += '</table>';
            html += '</div>';
            return html;

        },

        search: function (data, year, month, day) {
            for (i = 0; i < data.CalendarWeek.length; i++) {
                for (j = 0; j < data.CalendarWeek[i].CalendarDate.length; j++) {
                    if (data.CalendarWeek[i].CalendarDate[j].Year == year &&
                        data.CalendarWeek[i].CalendarDate[j].Month == month &&
                        data.CalendarWeek[i].CalendarDate[j].Day == day) {
                        return data.CalendarWeek[i].CalendarDate[j];
                    }
                }
            }
            return null;
        },
        getStatus: function (data, i) {
            var ItemStatus = [];
            for (k = 0; k < data.CalendarWeek[i].CalendarDate.length; k++) {
                for (l = 0; l < data.CalendarWeek[i].CalendarDate[k].Data.length; l++) {
                    if (ItemStatus.length == 0) {
                        ItemStatus[ItemStatus.length] = data.CalendarWeek[i].CalendarDate[k].Data[l].Status;
                    } else {
                        var ishav = false;
                        for (m = 0; m < ItemStatus.length; m++) {
                            if (ItemStatus[m] == 3 && data.CalendarWeek[i].CalendarDate[k].Data[l].Status == 3) {
                                ishav = true; break;
                            }
                            if (ItemStatus[m] != 3 && data.CalendarWeek[i].CalendarDate[k].Data[l].Status != 3) {
                                ishav = true; break;
                            }
                        }
                        if (!ishav) {
                            ItemStatus[m] = data.CalendarWeek[i].CalendarDate[k].Data[l].Status;
                        }
                    }
                }
            }
            return ItemStatus;
        },
        setHtml: function (data, i, j, left, right, isapprove, func, ItemStatus) {
            var currentDate = new Date();
            var html = "";
            for (s = 0; s < ItemStatus.length; s++) {
                for (k = 0; k < data.CalendarCatetory.length; k++) {
                    var text = "";
                    for (l = 0; l < data.CalendarWeek[i].CalendarDate[j].Data.length; l++) {
                        if (data.CalendarWeek[i].CalendarDate[j].Data[l].ID == data.CalendarCatetory[k].ID) {
                            if ((ItemStatus.length == 1) ||
                            (ItemStatus.length > 1 && ((s == 0 && data.CalendarWeek[i].CalendarDate[j].Data[l].Status == 3) ||
                                (s != 0 && data.CalendarWeek[i].CalendarDate[j].Data[l].Status != 3)))) {
                                var item = data.CalendarWeek[i].CalendarDate[j].Data[l];
                                var leftV = "", rightV = "";
                                if (left != null) { eval('leftV = item.' + left); if (leftV == null) leftV = ""; }
                                if (right != null) { eval('rightV = item.' + right); if (rightV == null) rightV = ""; }
                                if (func == null) {
                                    if (isapprove != null && isapprove) {
                                        if ((currentDate.getFullYear() < data.CalendarWeek[i].CalendarDate[j].Year) ||
                                            ((currentDate.getFullYear() == data.CalendarWeek[i].CalendarDate[j].Year) && (currentDate.getMonth() + 1) < data.CalendarWeek[i].CalendarDate[j].Month) ||
                                            ((currentDate.getFullYear() == data.CalendarWeek[i].CalendarDate[j].Year) && (currentDate.getMonth() + 1) == data.CalendarWeek[i].CalendarDate[j].Month) && (currentDate.getDate() <= data.CalendarWeek[i].CalendarDate[j].Day)) {
                                            switch (item.Status) {
                                                case 1: //待审核
                                                    if (item.IsMulte) {
                                                        text = '<span class="l">' + leftV + '</span><span class="r">' + rightV + '▲</span>';
                                                    } else {
                                                        text = '<span class="l">' + leftV + '</span><span class="r">' + rightV + '</span>';
                                                    }
                                                    break;
                                                case 2: //待审核
                                                    if (item.Active == "F") {
                                                        if (item.IsMulte) {
                                                            text = '<span class="l del">' + leftV + '</span><span class="r del">' + rightV + '▲</span>';
                                                        } else {
                                                            text = '<span class="l del">' + leftV + '</span><span class="r del">' + rightV + '</span>';
                                                        }
                                                    } else {
                                                        if (item.IsMulte) {
                                                            text = '<span class="l audit">' + leftV + '</span><span class="r audit">' + rightV + '▲</span>';
                                                        } else {
                                                            text = '<span class="l audit">' + leftV + '</span><span class="r audit">' + rightV + '</span>';
                                                        }
                                                    }
                                                    break;
                                                case 3: //审批通过
                                                    if (item.IsMulte) {
                                                        text = '<span class="l pas">' + leftV + '</span><span class="r pas">' + rightV + '▲</span>';
                                                    } else {
                                                        text = '<span class="l pas">' + leftV + '</span><span class="r pas">' + rightV + '</span>';
                                                    }
                                                    break;
                                                case 4: //审批否决
                                                    if (item.IsMulte) {
                                                        text = '<span class="l refuse">' + leftV + '</span><span class="r refuse">' + rightV + '▲</span>';
                                                    } else {
                                                        text = '<span class="l refuse">' + leftV + '</span><span class="r refuse">' + rightV + '</span>';
                                                    }
                                                    break;
                                            }
                                        } else {
                                            if (item.IsMulte) {
                                                text = '<span class="l grey">' + leftV + '</span><span class="r grey">' + rightV + '▲</span>';
                                            } else {
                                                text = '<span class="l grey">' + leftV + '</span><span class="r grey">' + rightV + '</span>';
                                            }
                                        }
                                        break;
                                    } else {
                                        if ((currentDate.getFullYear() < data.CalendarWeek[i].CalendarDate[j].Year) ||
                                            ((currentDate.getFullYear() == data.CalendarWeek[i].CalendarDate[j].Year) && (currentDate.getMonth() + 1) < data.CalendarWeek[i].CalendarDate[j].Month) ||
                                            ((currentDate.getFullYear() == data.CalendarWeek[i].CalendarDate[j].Year) && (currentDate.getMonth() + 1) == data.CalendarWeek[i].CalendarDate[j].Month) && (currentDate.getDate() <= data.CalendarWeek[i].CalendarDate[j].Day)) {
                                            text = '<span class="l pas">' + leftV + '</span><span class="r pas">' + rightV + '</span>';
                                        } else {
                                            text = '<span class="l grey">' + leftV + '</span><span class="r grey">' + rightV + '</span>';
                                        }
                                    }
                                } else {
                                    text = func(data.CalendarWeek[i].CalendarDate[j].Data[l]);
                                }
                            }
                        }
                    }
                    if ((ItemStatus.length == 1 && k == data.CalendarCatetory.length - 1) || (s == 1 && k == data.CalendarCatetory.length - 1)) {
                        html += '<p class="none_border">' + text + '</p>';
                    } else {
                        html += '<p>' + text + '</p>';
                    }
                }
            }
            return html;
        }
    }

    //比较
    $.compare = {
        date: function (b, e, msg) {
            if (b == null && e == null) {
                return true;
            }
            if (new Date(Date.parse(b.replace(/-/g, "/"))) > new Date(Date.parse(e.replace(/-/g, "/")))) {
                $.showModalMessageBox("最小" + msg + "不能大于最大" + msg + "!");
                return false;
            }
            return true;
        },
        dateMsg: function (b, e, msg) {
            if (b == null && e == null) {
                return true;
            }
            if (new Date(Date.parse(b.replace(/-/g, "/"))) > new Date(Date.parse(e.replace(/-/g, "/")))) {
                $.showModalMessageBox(msg);
                return false;
            }
            return true;
        },
        int: function (b, e, msg) {
            if (new Number(b) > new Number(e)) {
                $.showModalMessageBox(msg);
                return false;
            }
            return true;
        },

        number: function (b, e, msg) {
            if (Number(b) > Number(e)) {
                $.showModalMessageBox("最小" + msg + "不能大于最大" + msg + "!");
                return false;
            }
            return true;
        }
    }

    $.input = {
        init: function () {
            $("input[type='text']").each(function (i, e) {
                if ($(e).attr("id") != null) {

                    if (($(e).attr("id").indexOf("PMEID") != -1 || $(e).attr("id").indexOf("PAEID") != -1)) {
                        $(e).keyup(function () {
                            $(this).val($(this).val().replace("，", ",")); //全角逗号转换成半角
                            $(this).val($(this).val().replace("。", ".")); //全角句号转换成半角
                            $(this).val($(this).val().replace("＼", "、")); //全角顿号转换成半角
                            $(this).val($(this).val().replace("；", ";")); //全角逗号转换成半角
                            $(this).val($(this).val().replace(/[\u4e00-\u9fa5|;|\s]/g, '')); //过滤掉半角分号、空格以及任何汉字
                        }).bind("paste", function () {
                            $(this).val($(this).val().replace("，", ",")); //全角逗号转换成半角
                            $(this).val($(this).val().replace("。", ".")); //全角句号转换成半角
                            $(this).val($(this).val().replace("＼", "、")); //全角顿号转换成半角
                            $(this).val($(this).val().replace("；", ";")); //全角逗号转换成半角
                            $(this).val($(this).val().replace(/[\u4e00-\u9fa5|;|\s]/g, '')); //过滤掉半角分号、空格以及任何汉字
                        }).css("ime-mode", "disabled");
                    }


                    if (($(e).attr("id").indexOf("HotelIDs") != -1 || $(e).attr("id").indexOf("RoomIDs") != -1) ||
                        ($(e).attr("id").indexOf("LineTourIDs") != -1 || $(e).attr("id").indexOf("ResourceIDs") != -1)) {
                        $(e).keyup(function (event) {

                            if (event.keyCode >= 35 && event.keyCode <= 39) {
                            } else {
                                var isInt = /[\d\,]$/
                                if (!isInt.test($(this).val())) {
                                    $(this).val($(this).val().replace("，", ",")); //全角逗号转换成半角
                                    $(this).val($(this).val().replace(/[^\d\,]/g, ''));
                                }
                            }
                        }).bind("paste", function () {
                            var isInt = /[\d\,]$/
                            if (!isInt.test($(this).val())) {
                                $(this).val($(this).val().replace("，", ",")); //全角逗号转换成半角
                                $(this).val($(this).val().replace(/[^\d\,]/g, ''));
                            }
                        }).css("ime-mode", "disabled");
                    }

                    if ($(e).attr("id").indexOf("AdvanceBookingTime") != -1) {
                        $(e).css("ime-mode", "disabled");
                    }

                    if ($(e).attr("id").indexOf("MaxVoucherAmount") != -1 || $(e).attr("id").indexOf("MaxTravelDays") != -1 ||
                        $(e).attr("id").indexOf("MinTravelDays") != -1 || $(e).attr("id").indexOf("MinPersonQuantity") != -1 ||
                        $(e).attr("id").indexOf("MaxPersonQuantity") != -1 || $(e).attr("id").indexOf("EffectDays") != -1 || $(e).attr("id").indexOf("TransportationID") != -1 ||
                        $(e).attr("id").indexOf("SortNum") != -1 || $(e).attr("id").indexOf("Vendor_ID") != -1 || $(e).attr("id").indexOf("txtEditSortNum") != -1 || $(e).attr("id").indexOf("txtSelectedTagQuantityLimit") != -1 || $(e).attr("id").indexOf("txtSequenceNumber") != -1 || $(e).attr("id").indexOf("txtToProductID") != -1 || $(e).attr("id").indexOf("VendorID") != -1 ||

                        ($(e).attr("id").indexOf("RoomIDs") == -1 && $(e).attr("id").indexOf("RoomID") != -1) || $(e).attr("id").indexOf("IResourceID") != -1
                        || $(e).attr("id").indexOf("OResourceID") != -1 || ($(e).attr("id").indexOf("ItemIDs") == -1 && $(e).attr("id").indexOf("ItemID") != -1)
                        || ($(e).attr("id").indexOf("ResourceIDs") == -1 && $(e).attr("id").indexOf("ResourceID") != -1)) {
                        $(e).keyup(function () {
                            $(this).val($(this).val().replace(/\D/g, '')); //只能输入正整数
                        }).bind("paste", function () {
                            $(this).val($(this).val().replace(/\D/g, '')); //只能输入正整数
                        }).css("ime-mode", "disabled");
                    }

                }
            });
        }
    }

    $.scroll = {
        init: function (element) {
            $(document.body).scroll(function () {
                var window_top = $(this).scrollTop();
                if (window_top >= obj_top) {
                    if (!$.browser.msie || ($.browser.msie && $.browser.version >= 7)) {
                        element.css({
                            position: "fixed",
                            top: 10
                        });
                    } else {
                        element.css({
                            position: "absolute",
                            top: window_top + 10
                        });
                    }
                } else {
                    element.css("position", "static");
                }
            });
        }
    }

    $.calender = {
        init: function () {
            $("input[type='text']").each(function (i, e) {
                if ($(e).attr("mod") == null || $(e).attr("mod").indexOf("calendar") == -1) {
                    return;
                }
                $(e).bind("click", function () {
                    WdatePicker({
                        doubleCalendar: true, dateFmt: 'yyyy-MM-dd'
                    })
                });
                $(e).bind("keydown", function () { $(e).val(""); return false; });
            });
        }
    }


    $.fn.extend({
        cPaging: function (p) {

            var pager = {
                //控件对象
                controls: {},
                option: {},
                renderLeft: function (srcEle, total) {
                    var lhtml = "";

                    //<div class="pagination-info">共有51条，每页显示：50条</div>
                    //lhtml += "<div class=\"pagination-info\">共有<span>100</span>条，每页显示：<label>20</label>条</div>";
                    lhtml += "<div class=\"pagination-info\">共有<span>100</span>条，每页显示：<select class='case-form-control' style='width:50px; height:30px' name='Pagination_PageSize' > <option selected='selected' value='10'>10</option><option selected='selected' value='15'>15</option><option >20</option> <option value='50'>50</option><option value='100'>100</option> <option value='200'>200</option></select> 条</div>";
                    pager.option.srcEle.html(lhtml);
                    pager.controls.selPageSize = srcEle.find("select");
                    
                    pager.controls.selPageSize.val(pager.controls.hid_pageSize.val() || 20);        //分页大小选择下拉框
                    srcEle.find("div span").text(total);
                    //srcEle.find("div label").text(pager.controls.hid_pageSize.val() || 20);

                },
                bind: function (f, args, scope) {
                    scope = scope || window;
                    return function () {

                        return f.call(scope, args);
                    }
                },

                //分页Render
                renderRight: function (totalCount, pageNo, pageSize, totoalPageSize, srcEle) {

                    var rhtml = "";
                    rhtml += "<ul class=\"pagination\">";
                    rhtml += "<li class=\"c_first\"> <a class=\"c_first\">«</a> </li>";
                    rhtml += "<li class=\"c_pre\"> <a class=\"c_pre\">‹</a> </li>";

                    if (eval(pageNo) > 5) {

                        rhtml += "<li><a>1</a></li>";
                        rhtml += "<li><span>...</span></li>";

                        for (var i = 0; i < 3; i++) {
                            rhtml += "<li><a>" + (pageNo - 3 + i) + "</a></li>";
                        }

                        rhtml += "<li class='active'><a>" + (pageNo - 3 + i) + "</a></li>";
                    }
                    else {
                        for (var i = 0; i < pageNo; i++) {
                            if (i + 1 == pageNo) {
                                rhtml += "<li class='active'><a>" + (i + 1) + "</a></li>";
                            }
                            else {
                                rhtml += "<li><a>" + (i + 1) + "</a></li>";
                            }
                        }
                    }
                    if (eval(pageNo) + 3 < eval(totoalPageSize) - 1) {
                        for (var i = 0; i < 3; i++) {
                            //rhtml += "<li class='active'><a>" + (pageNo + i + 1) + "</a></li>";
                            rhtml += "<li><a>" + (pageNo + i + 1) + "</a></li>";
                        }
                        rhtml += "<li><span>...</span></li>";
                        rhtml += "<li><a>" + totoalPageSize + "</a></li>";
                    }
                    else {
                        for (var i = 0; i < eval(totoalPageSize - pageNo) ; i++) {
                            rhtml += "<li><a>" + (pageNo + i + 1) + "</a></li>";
                        }
                    }

                    rhtml += " <li class=\"c_next\"> <a class=\"c_next\">›</a> </li>";
                    rhtml += " <li class=\"c_last\"> <a class=\"c_last\">»</a> </li>";
                    rhtml += " </ul>";

                    rhtml += "<div class=\"pagination-goto\">";
                    rhtml += "    <input type='text' class='ipt form-control' style='height:30px' id='gotoPageNo' value=" + pageNo + ">";
                    rhtml += "    <input type='hidden' id='totalCount' name='totalCount' value=" + totalCount + ">";
                    rhtml += "    <input type='text' id='totalCount_text' style='display:none' >";
                    rhtml += "    <input type='button' class='btn btn-default' style='height:30px' id='goBtn' value='GO'></input>";

                    rhtml += "</div>";

                    if (srcEle.find(".pagination").length)
                        srcEle.find(".pagination").html(rhtml);
                    else
                        srcEle.append(rhtml);

                    if (pageNo <= 1) {
                        srcEle.find("li.c_first").attr("class", "disabled");
                        srcEle.find("li.c_pre").attr("class", "disabled");
                    }
                    if (pageNo >= totoalPageSize) {
                        srcEle.find("li.c_last").attr("class", "disabled");
                        srcEle.find("li.c_next").attr("class", "disabled");
                    }

                    pager.controls.container = srcEle;      //容器ul class="info_inall layoutfix"
                    pager.controls.inputPageNum = srcEle.find("input.ipt");   //输入页数框
                    pager.controls.pageFirst = srcEle.find("a.c_first");      //首页按钮
                    pager.controls.pageUp = srcEle.find("a.c_pre");      //上一页按钮
                    pager.controls.pageDown = srcEle.find("a.c_next");      //下一页按钮
                    pager.controls.pageLast = srcEle.find("a.c_last");      //末页按钮
                    pager.controls.btnGo = srcEle.find("input.btn");      //跳转到指定页

                }, //end of drawPaging


                //分页Action
                drawPagingAction: function (pageNo, totoalPageSize, pageSize) {
                    $("a", pager.controls.container).each(function () {
                        $(this).click(function () {

                            var cName = $(this).attr("class");
                            switch (cName) {
                                case "c_first":
                                    if (pageNo <= 1) return;
                                    pager.controls.hid_pageNo.val(1);
                                    break;
                                case "c_pre":
                                    if (pageNo <= 1) return;
                                    pager.controls.hid_pageNo.val(--pageNo);
                                    break;
                                case "c_next":
                                    if (pageNo >= totoalPageSize) return;
                                    pager.controls.hid_pageNo.val(++pageNo);
                                    break;
                                case "c_last":
                                    if (pageNo >= totoalPageSize) return;
                                    pager.controls.hid_pageNo.val(totoalPageSize);
                                    break;
                                default:
                                    pager.controls.hid_pageNo.val($(this).text());
                                    break;
                            }
                            
                            pager.controls.hid_pageSize.val(pageSize);
                            if (pager.option.callBack) {
                                var func = pager.bind(pager.option.callBack, pager.option.callBackArgs, null);
                                func();
                            }
                        });
                    });


                    //确定按钮
                    pager.controls.btnGo.click(function () {
                        if (pager.controls.inputPageNum.val() == "") {
                            alert("请输入页码数");
                            pager.controls.inputPageNum.focus();
                            return;
                        }
                        var isIntVal = /^[0-9]*[1-9][0-9]*$/;

                        if (!isIntVal.test(pager.controls.inputPageNum.val())) {
                            alert("请输入正确的页码!");
                            return;
                        }
                        if (Number(pager.controls.inputPageNum.val()) > pager.option.totoalPageSize) {
                            alert("请输入有效范围的页码!");
                            return;
                        }

                        
                        pager.controls.hid_pageSize.val(pager.controls.selPageSize.val());
                        pager.controls.hid_pageNo.val(pager.controls.inputPageNum.val());

                        if (pager.option.callBack) {
                            var func = pager.bind(pager.option.callBack, pager.option.callBackArgs, null);

                            func();
                        }
                    });

                    //用户改变分页大小
                    pager.controls.selPageSize.change(function () {
                        pager.controls.hid_pageSize.val($(this).val());
                        pager.controls.hid_pageNo.val(pager.controls.inputPageNum.val());

                        if (pager.option.totalCount / Number($(this).val()) < Number(pager.controls.inputPageNum.val())) {
                            pager.controls.hid_pageNo.val(1);
                        }

                        if (pager.option.callBack) {
                            var func = pager.bind(pager.option.callBack, pager.option.callBackArgs, null);

                            func();
                        }
                    });

                },

                init: function (p, srcEle) {
                    var isPaging = true;

                    pager.option = p || { totalCount: 100, pageNo: 1, pageSize: 20, callBack: null, callBackArgs: null };

                    pager.option.srcEle = srcEle;
                    pager.controls.hid_pageNo = $('input[name$="PageNo"]');         //隐藏控件，页号
                    pager.controls.hid_pageSize = $('input[name$="PageSize"]');     //隐藏控件，分页大小
                    //pager.controls.hid_pageSize = $('select[name$="Pagination_PageSize"]');     //隐藏控件，分页大小

                    

                    if (pager.option.totalCount < 1 || pager.option.pageNo < 1)
                        isPaging = false;

                    pager.option.totoalPageSize = Math.ceil(pager.option.totalCount / pager.option.pageSize);

                    if (pager.option.pageNo > pager.option.totoalPageSize)
                        isPaging = false;

                    if (isPaging) {
                        pager.renderLeft(pager.option.srcEle, pager.option.totalCount);
                        pager.renderRight(pager.option.totalCount, pager.option.pageNo, pager.option.pageSize, pager.option.totoalPageSize, pager.option.srcEle);
                        pager.drawPagingAction(pager.option.pageNo, pager.option.totoalPageSize, pager.option.pageSize);
                    }
                }
            };

            pager.init(p, $(this));

        } //end of extend
    });

    $.fn.extend({
        iPaging: function (p) {

            var pager = {
                //控件对象
                controls: {},
                option: {},
                renderLeft: function (srcEle, total) {
                    var lhtml = "";
                    lhtml += "<li class=\"left\">共<span>100</span>条&nbsp;&nbsp;每页显示&nbsp;";
                    lhtml += " <select style=\"width: 50px;\">";
                    lhtml += "     <option value='10'>10</option>";
                    lhtml += "     <option value='20'>20</option>";
                    lhtml += "     <option value='50'>50</option>";
                    lhtml += "     <option value='100'>100</option>";
                    lhtml += " </select>&nbsp;条</li>";
                    pager.option.srcEle.html(lhtml);

                    pager.controls.selPageSize = srcEle.find("select");        //分页大小选择下拉框

                    srcEle.find("li.left span").text(total);

                    pager.controls.selPageSize.val(pager.controls.hid_pageSize.val() || 50);

                },
                bind: function (f, args, scope) {
                    scope = scope || window;
                    return function () {

                        return f.call(scope, args);
                    }
                },

                //分页Render
                renderRight: function (totalCount, pageNo, pageSize, totoalPageSize, srcEle) {

                    var rhtml = "";
                    rhtml += "<li class=\"right\"><div class=\"c_page\"><a class=\"c_up\" href=\"javascript:void(0);\">上一页</a>";
                    rhtml += "<div class=\"c_page_list layoutfix\">";
                    if (eval(pageNo) > 5) {

                        rhtml += "<a href=\"javascript:void(0)\">1</a>";
                        rhtml += "<span class=\"c_page_ellipsis\">...</span>";
                        for (var i = 0; i < 3; i++) {
                            rhtml += "<a href=\"javascript:void(0)\">" + (pageNo - 3 + i) + "</a>";
                        }
                        rhtml += "<a href=\"javascript:void(0)\" class=\"current\">" + (pageNo - 3 + i) + "</a>";
                    }
                    else {
                        for (var i = 0; i < pageNo; i++) {
                            if (i + 1 == pageNo) {
                                rhtml += "<a href=\"javascript:void(0)\" class=\"current\">" + (i + 1) + "</a>";
                            }
                            else {
                                rhtml += "<a href=\"javascript:void(0)\">" + (i + 1) + "</a>";
                            }
                        }
                    }
                    if (eval(pageNo) + 3 < eval(totoalPageSize) - 1) {
                        for (var i = 0; i < 3; i++) {
                            rhtml += "<a href=\"javascript:void(0)\">" + (pageNo + i + 1) + "</a>";
                        }
                        rhtml += "<span class=\"c_page_ellipsis\">...</span>";
                        rhtml += "<a href=\"javascript:void(0)\">" + totoalPageSize + "</a>";
                    }
                    else {
                        for (var i = 0; i < eval(totoalPageSize - pageNo) ; i++) {
                            rhtml += "<a href=\"javascript:void(0)\">" + (pageNo + i + 1) + "</a>";
                        }
                    }
                    rhtml += "</div>";
                    rhtml += "<a class=\"c_down\" href=\"javascript:void(0);\">下一页</a>";
                    rhtml += "<div class=\"c_pagevalue\">到<input type=\"text\" name=\"\" class=\"c_page_num\"  value=\"" + pageNo + "\" />页<input type=\"button\" name=\"\" value=\"确定\" class=\"c_page_submit\"  /></div></div><li>";

                    if (srcEle.find("li.right").length)
                        srcEle.find("li.right").html(rhtml);
                    else
                        srcEle.append(rhtml);



                    pager.controls.container = srcEle;      //容器ul class="info_inall layoutfix"
                    pager.controls.inputPageNum = srcEle.find("input.c_page_num");   //输入页数框
                    pager.controls.pageUp = srcEle.find("a.c_up");      //上一页按钮
                    pager.controls.pageDown = srcEle.find("a.c_down");      //下一页按钮
                    pager.controls.btnGo = srcEle.find("input.c_page_submit");      //跳转到指定页



                }, //end of drawPaging


                //分页Action
                drawPagingAction: function (pageNo, totoalPageSize, pageSize) {

                    pager.controls.container.find("div.c_page>a.c_down,div.c_page>a.c_up,div.c_page_list.layoutfix>a").click(function () {
                        var cName = $(this).attr("class");

                        switch (cName) {
                            case "c_up":
                                if (pageNo <= 1) return;
                                pager.controls.hid_pageNo.val(--pageNo);
                                break;
                            case "c_down":
                                if (pageNo >= totoalPageSize) return;
                                pager.controls.hid_pageNo.val(++pageNo);
                                break;
                            default:
                                pager.controls.hid_pageNo.val($(this).text());
                                break;
                        }
                        pager.controls.hid_pageSize.val(pageSize);
                        if (pager.option.callBack) {
                            var func = pager.bind(pager.option.callBack, pager.option.callBackArgs, null);

                            func();
                        }


                    });


                    //确定按钮
                    pager.controls.btnGo.click(function () {
                        if (pager.controls.inputPageNum.val() == "") {
                            alert("请输入页码数");
                            pager.controls.inputPageNum.focus();
                            return;
                        }
                        var isIntVal = /^[0-9]*[1-9][0-9]*$/;

                        if (!isIntVal.test(pager.controls.inputPageNum.val())) {
                            alert("请输入正确的页码!");
                            return;
                        }
                        if (Number(pager.controls.inputPageNum.val()) > pager.option.totoalPageSize) {
                            alert("请输入有效范围的页码!");
                            return;
                        }


                        //pager.controls.hid_pageSize.val(pager.controls.selPageSize.val());
                        pager.controls.hid_pageNo.val(pager.controls.inputPageNum.val());

                        if (pager.option.callBack) {
                            var func = pager.bind(pager.option.callBack, pager.option.callBackArgs, null);

                            func();
                        }
                    });

                    //用户改变分页大小
                    pager.controls.selPageSize.change(function () {
                        pager.controls.hid_pageSize.val($(this).val());
                        pager.controls.hid_pageNo.val(pager.controls.inputPageNum.val());

                        if (pager.option.totalCount / Number($(this).val()) < Number(pager.controls.inputPageNum.val())) {
                            pager.controls.hid_pageNo.val(1);
                        }

                        if (pager.option.callBack) {
                            var func = pager.bind(pager.option.callBack, pager.option.callBackArgs, null);

                            func();
                        }
                    });

                },

                init: function (p, srcEle) {
                    var isPaging = true;

                    pager.option = p || { totalCount: 100, pageNo: 1, pageSize: 50, callBack: null, callBackArgs: null };


                    pager.option.srcEle = srcEle;
                    pager.controls.hid_pageNo = $('input[name$="PageNo"]');         //隐藏控件，页号
                    pager.controls.hid_pageSize = $('input[name$="PageSize"]');     //隐藏控件，分页大小

                    if (pager.option.totalCount < 1 || pager.option.pageNo < 1)
                        isPaging = false;


                    pager.option.totoalPageSize = Math.ceil(pager.option.totalCount / pager.option.pageSize);


                    if (pager.option.pageNo > pager.option.totoalPageSize)
                        isPaging = false;

                    if (isPaging) {
                        pager.renderLeft(pager.option.srcEle, pager.option.totalCount);
                        pager.renderRight(pager.option.totalCount, pager.option.pageNo, pager.option.pageSize, pager.option.totoalPageSize, pager.option.srcEle);
                        pager.drawPagingAction(pager.option.pageNo, pager.option.totoalPageSize, pager.option.pageSize);
                    }

                }
            };


            pager.init(p, $(this));



        } //end of extend
    });

})(jQuery);



/************************************************************************/
/* DateTime转换成Json                                                   */
/************************************************************************/
function convertJsonDateToJSDate(jsonDate) {
    var date = new Date(parseInt(jsonDate.replace("/Date(", "").replace(")/", ""), 10));
    return date;
}

/* 获取日期格式 */
function getDate(date) {
    var year = date.getFullYear();
    var month = date.getMonth() + 1;
    var day = date.getDate();
    return year + "-" + month + "-" + day;
}
/* 获取日期时间格式*/
function getDateTime(date) {
    var year = date.getFullYear();
    var month = date.getMonth() + 1;
    var day = date.getDate();
    var hh = date.getHours();
    var mm = date.getMinutes();
    var ss = date.getSeconds();
    return year + "-" + month + "-" + day + " " + hh + ":" + mm + ":" + ss;
}

//验证是否为数字
function isNumber(num) {
    if (!num) {
        return false;
    }
    var reNum = /^\d*$/;
    return (reNum.test(num));
}

function isNumberic(str) {
    var re = /^[0-9]+.?[0-9]*$/;   //判断字符串是否为数字     //判断正整数 /^[1-9]+[0-9]*]*$/   
    if (!re.test(str)) {
        return false;
    }
    return true;
}

function AssociateMagr(ctlid, ctlname, div, api, data, objexpname, ctlctyID, ctlctyName, ctScenicSpotID) {
    this.GlobalID = $(ctlid).val();
    this.GlobalName = $(ctlname).val();
    this.Event = null;

    this.Associate = function (obj) {
        //拼接对象
        var data1 = "{";
        for (var k in data) {
            var v = data[k];
            if (typeof (v) != "object") { data1 += k + ":\"" + v + "\","; }
            else { data1 += k + ":\"" + v.val() + "\","; }
        }
        data1 = data1.substr(0, data1.length - 1);
        data1 += "}";

        var id = ctlid.val();
        var name = ctlname.val();
        if ($.trim(name) == "") { return false; }

        $.ajaxPost(api, eval("(" + data1 + ")"), function (response) {
            $(div).find(".c_address_list").empty();
            if (response.IsSuccess) {
                $.each(response.Data, function (i, e) {
                    var html = $("<a href='javascript:void(0)'>" + e.Name + "</a>");
                    //                    if (e.Name != null && e.Name != "") {
                    //                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em></a>");
                    //                    }
                    if (e.ScenicSpotName != null && e.ScenicSpotName != "") {
                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>/(" + e.ScenicSpotName + ")</em></a>");
                    }
                    else if (e.ProvinceName != null && e.ProvinceName != "") {
                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>(" + e.ProvinceName + ")</em></a>");
                    }
                    else if (e.CountryName != null && e.CountryName != "") {
                        if (e.HasAirport == true) {
                            html = $("<a href='javascript:void(0)'>" + e.Name + "--有机场<em>(" + e.CountryName + ")</em></a>");
                        }
                        else if (e.HasAirport == false) {
                            html = $("<a href='javascript:void(0)'>" + e.Name + "--无机场<em>(" + e.CountryName + ")</em></a>");
                        }
                        else {
                            html = $("<a href='javascript:void(0)'>" + e.Name + "<em>(" + e.CountryName + ")</em></a>");
                        }
                    }
                    else if (e.Area != null && e.Area.Name != "") {
                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>(" + e.Area.Name + ")</em></a>");
                    }
                    //                    else if (e.ScenicSpotName != null && e.ScenicSpotName != "") {
                    //                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>/(" + e.ScenicSpotName + ")</em></a>");
                    //                    }
                    if (e.DistrictName != null && e.DistrictName != "") {
                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>/(" + e.DistrictName + ")</em></a>");
                    }

                    if (e.HotelName != null && e.HotelName != "") {
                        html = $("<a href='javascript:void(0)'>" + e.HotelName + "<em>/(" + e.HotelName + ")</em></a>");
                    }

                    //                    else {
                    //                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>(" + e.ProvinceName + ")</em></a>");
                    //                    }

                    //                    if (e.ProvinceName != null && e.ProvinceName != "") {
                    //                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>(" + e.ProvinceName + ")</em></a>");
                    //                    } else if (e.CountryName != null && e.CountryName != "") {
                    //                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>(" + e.CountryName + ")</em></a>");
                    //                    } else if (e.Area != null && e.Area.Name != "") {
                    //                        html = $("<a href='javascript:void(0)'>" + e.Name + "<em>(" + e.Area.Name + ")</em></a>");
                    //                    }


                    $(div).find(".c_address_list").append(html);
                    html.click(function () {
                        if (e.ScenicSpotName != null && e.ScenicSpotName != "") {
                            var temp = e.Name + "/" + e.ScenicSpotName;
                            $(ctlname).val(temp);
                        } else if (e.ProvinceName != null && e.ProvinceName != "") {
                            $(ctlname).val(e.Name);
                        }
                        else if (e.CountryName != null && e.CountryName != "") {
                            $(ctlname).val(e.Name);
                        } else if (e.Area != null && e.Area.Name != null && objexpname != null) {
                            $(ctlname).val(e.Name);
                            $(objexpname).html(e.Area.Name);
                        }

                        else if (e.HotelName != null) {
                            $(ctlname).val(e.HotelName);
                            $("#hiddenHotelName").val(e.HotelName);
                            //$(objexpname).html(e.Area.Name);
                        }

                        else {
                            $(ctlname).val(e.Name);
                        }


                        //                        if (e.ProvinceName != null && e.ProvinceName != "") {
                        //                            $(ctlname).val(e.Name);
                        //                        } else if (e.CountryName != null && e.CountryName != "") {
                        //                            $(ctlname).val(e.Name);
                        //                        } else if (e.Area != null && e.Area.Name != null && objexpname != null) {
                        //                            $(ctlname).val(e.Name);
                        //                            $(objexpname).html(e.Area.Name);
                        //                        }
                        //                        else {
                        //                            $(ctlname).val(e.Name);
                        //                        }


                        $(ctlid).val(e.ID);
                        if (e.CountryID != null) {
                            $(ctlctyID).val(e.CountryID);
                            if ($(ctlctyName).length > 0) {
                                if ($(ctlctyName).attr("id") == "ResourceModel_DestinationCountry_Name") {//如果是资源维护页
                                    var res_cus_temp = $("#ResourceModel_CustomerInfoTemplateID");
                                    if (res_cus_temp.length > 0) {
                                        if (e.CountryID <= 0) {
                                            ctlctyName.html("");
                                        }
                                        LoadCustomerInfoTemplate();
                                    }
                                }
                            }
                        }

                        if (e.ScenicSpotID != null) {
                            $(ctScenicSpotID).val(e.ScenicSpotID);
                        }

                        if (e.CountryName != null && e.CountryName != "") {
                            $(ctlctyName).html(e.CountryName);
                        }

                        if (e.HotelID != null) {
                            $(ctScenicSpotID).val(e.HotelID);
                            $("#HotelID").val(e.HotelID);
                        }

                        $(div).hide();
                        obj.GlobalName = e.Name;
                        obj.GlobalID = e.ID;
                        return false;
                    });
                });
            }
        }, false);
        $(div).css({
            "position": "absolute",
            "left": $(ctlname).offset().left,
            "top": $(ctlname).offset().top + 20,
            "z-index": 9999
        }).show();
    }
    $(ctlname).bind('keyup', { obj: this }, function (event) {
        if (event.keyCode == 38) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).prev().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).prev().addClass("hover");
                        $(hover).prev().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 40) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    if ($(hover).next().length > 0) {
                        $(hover).removeClass("hover");
                        $(hover).removeAttr("style");
                        $(hover).next().addClass("hover");
                        $(hover).next().css("background-color", "#E8F4FF");
                    }
                } else {
                    $($(div).find("a")[0]).css("background-color", "#E8F4FF");
                    $($(div).find("a")[0]).addClass("hover");
                }
            }
        } else if (event.keyCode == 13) {
            if ($(div).find("a").length > 0) {
                var hover = $(div).find("a[class='hover']");
                if (hover.length > 0) {
                    $(hover).click();
                }
            }
        } else {
            clearTimeout(event.data.obj.Event);
            event.data.obj.Event = setTimeout(function () { event.data.obj.Associate(event.data.obj); }, 500);
        }
    });

    $(ctlname).bind('blur', { obj: this }, function (event) {
        if ($(this).val() == "" || ($(this).val() == $(this).attr("mod-notice-tip"))) {
            event.data.obj.GlobalName = "";
            $(ctlid).val("");
            if ($(ctlctyID).length > 0) {
                $(ctlctyID).val("");
            }

            if ($(ctScenicSpotID).length > 0) {
                $(ctScenicSpotID).val("");
            }

            if ($(ctlctyName).length > 0) {
                $(ctlctyName).html("");
            }
            if ($(objexpname).length > 0) {
                $(objexpname).html("");
            }
        }
        if ($(ctlid).val() == "") {
            if ($(this).attr("mod-notice-tip")) {
                $(this).val($(this).attr("mod-notice-tip"));
            } else {
                $(this).val("");
            }
        }
        //        if (event.data.obj.GlobalName != "") {
        //            $(this).val(event.data.obj.GlobalName);
        //            $(ctlid).val(event.data.obj.GlobalID);
        //        }
    });

    return this;
}

//根据需求,在文本框输入后,按回车,直接查询
function EnterPress(e, btnID) { //传入 event和要获得焦点的控件,通用
    var e = e || window.event;
    if (e.keyCode == 13) {
        $("#" + btnID).focus();
    }
}

//获得产品线数据并赋值到下拉框
function initConfigHint() {
    var data = { id: 0 };
    var index = 0;
    var tips = "";
    $("label").each(function (i, e) {
        if ($(e).attr("hint") != null) {
            index++;
        }
    });

    if (index > 0) {

        $("label[hint!='']").each(function (i, e) {

            if ($(e).parent().find("span").html() == null) {
                $(e).parent().append("<span style='display:none' mod_jmpinfo_content=''></span>");
            }
            $(e).css("cursor", "hand")
            $(e).click(function () {
                if ($(e).attr("hint") != null) {
                    data.id = $(e).attr("hint");

                    if ($(e).parent().find("span").attr("mod_jmpinfo_content") == "") {

                        $.ajaxPost(AP_ROOT + "Product/ProductBase/GetConfigHint", data, function (response) {
                            if (response.IsSuccess) {
                                tips = "<h4>操作说明:</h4>" + response.Data.OperatingInstructions + "<br/><br/><h4>规则说明:</h4>" + response.Data.RuleDescription;
                                $(e).parent().find("span").attr("mod_jmpinfo_content", tips);
                                $(e).cTips().show();
                            } else {
                                alert("获取数据失败!");
                            }
                        });
                    }
                }
            });
        });
    }

}


//返回val的字节长度 
function StrLen(s) {
    var l = 0;
    for (var i = 0; i < s.length; i++) {
        if (s.charCodeAt(i) < 299) { l++; }
        else { l += 2; }
    }
    return l;
}

//遮罩层定位
function MaskCenter(obj) {
    var screenWidth = $(window).width();
    var screenHeight = $(window).height();
    var objLeft = (screenWidth - obj.width()) / 2;
    obj.css({ left: objLeft + 'px', 'display': 'block' });

    $(window).resize(function () {
        if (obj.css("display") == "block") {
            var screenWidth = $(window).width();

            var objLeft = (screenWidth - obj.width()) / 2;
            var strwidth = 0;
            if (screenWidth > 950) {
                strwidth = document.body.scrollWidth;
            }
            else if (screenWidth <= 600) {
                strwidth = screen.width;
            }
            else {
                strwidth = 1250;
            }
            obj.css({ left: objLeft + 'px', width: strwidth + 'px', 'display': 'block' });

        }
        else {
            obj.hide();
        }
    });
    $(window).scroll(function () {
        if (obj.css("display") == "block") {
            var screenWidth = $(window).width();

            var objLeft = (screenWidth - obj.width()) / 2;


            obj.css({ left: objLeft + 'px', 'display': 'block' });
        }
        else {
            obj.hide();
        }
    });
}

//定位函数
function center(obj) {

    var screenWidth = $(window).width();
    var screenHeight = $(window).height();
    var scrolltop = $(document).scrollTop();

    var objLeft = (screenWidth - obj.width()) / 2;
    var objTop = (screenHeight - obj.height()) / 2 + scrolltop;

    obj.css({ left: objLeft + 'px', top: objTop + 'px', 'display': 'block' });
    $(window).resize(function () {
        if (obj.css("display") == "block") {
            var screenWidth = $(window).width();
            var screenHeight = $(window).height();
            var scrolltop = $(document).scrollTop();
            var scrollLeft = $(document).scrollLeft();

            var objLeft = (screenWidth - obj.width()) / 2 + scrollLeft;
            var objTop = (screenHeight - obj.height()) / 2 + scrolltop;

            obj.css({ left: objLeft + 'px', top: objTop + 'px', 'display': 'block' });
        }
        else {
            obj.hide();
        }
    });
    $(window).scroll(function () {
        if (obj.css("display") == "block") {
            var screenWidth = $(window).width();
            var screenHeight = $(window).height();
            var scrolltop = $(document).scrollTop();
            var scrollLeft = $(document).scrollLeft();

            var objLeft = (screenWidth - obj.width()) / 2;
            var objTop = (screenHeight - obj.height()) / 2 + scrolltop;

            obj.css({ left: objLeft + 'px', top: objTop + 'px', 'display': 'block' });
        }
        else {
            obj.hide();
        }
    });

}

//UBT
//(function (window) {
//    var slist = document.getElementsByTagName('script') || [];
//    var reg = /_bfa\.min\.js/i;
//    for (var i = 0; i < slist.length; i++) {
//        if (reg.test(slist[i].src)) { return; }
//    };
//    if ((window.$_bf && window.$_bf.loaded) || window.$LAB || window.CtripJsLoader)
//    { return; };
//    window.__bfi = window.__bfi || [];
//    window.__bfi.push(["_delCollect", "performance,click"]);
//    window.__bfi.push(["_setEnv", "offline"]);
//    var d = new Date();
//    var v = '?v=' + d.getFullYear() + d.getMonth() + '_' + d.getDate();
//    var bf = document.createElement('script');
//    bf.type = 'text/javascript'; bf.charset = 'utf-8'; bf.async = true;
//    //bf.src = "http://webresint.sh.ctriptravel.com/code/ubt/_bfa.min.js" + v;
//    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(bf, s);
//})(window);


//查找子串
function contains(string, substr, isIgnoreCase) {
    if (isIgnoreCase) {
        string = string.toLowerCase();
        substr = substr.toLowerCase();
    }
    var startChar = substr.substring(0, 1);
    var strLen = substr.length;
    for (var j = 0; j < string.length - strLen + 1; j++) {
        if (string.charAt(j) == startChar)//如果匹配起始字符,开始查找
        {
            if (string.substring(j, j + strLen) == substr)//如果从j开始的字符与str匹配，那ok
            {
                return true;
            }
        }
    }
    return false;
}

