// Js prerequisites: 
// site_bootstrap.js
window.CONST_MODE_LGN = 0;
window.CONST_MODE_REG = 1;
window.CONST_MODE_FGP = 2;
window.CONST_MODE_WIDGETLGN = 3;
window.CONST_MODE_VIASNLGN = 4;

window.CONST_JSSTORE_AUTH = "gr_auth";
window.CONST_JSSTORE_EMAIL = "gr_def_email";
window.CONST_JSSTORE_REGOK = "gr_regsuc";
window.CONST_JSSTORE_INVBY = "gr_invby";
window.CONST_JSSTORE_REFER = "gr_refer";
window.CONST_JSSTORE_REFERURL = "gr_referurl";
window.CONST_JSSTORE_SOCNLA = "gr_socnla";
window.CONST_HYBRIDAUTH_URL = "http://www.gamerotor.com/php/hybridauth/gr_main.php?provider=";
window.CONST_GUEST_PREFIX = "Guest";
window.CONST_GUEST_PSW = "***";
window.FLAG_ADVANCEDJS_LOADED = 0;
window.CONST_ZINDEX_LOGIN = 200;


window.FLAGS_USER_ISREAL     = 1
window.FLAGS_USER_ISCHEATER  = 2
window.FLAGS_USER_SUBSCRIBED = 4
window.FLAGS_USER_SOCPRESENT = 8

window.SOCBTN_SHAREPLUSO = [
	"facebook","google","vkontakte","odnoklassniki","moimir"
];
window.SOCBTN_SHARE42 = [
	["Facebook","<div class='socn_facebook inline_img %(common_class)' prov='Facebook' title='Facebook'></div>"],
	["Vkontakte","<div class='socn_vkontakte inline_img %(common_class)' prov='Vkontakte' title='VKontakte'></div>"],
	["Odnoklassniki","<div class='socn_odnoklassniki inline_img %(common_class)' prov='Odnoklassniki' title='Odnoklassniki'></div>"],
	["Google","<div class='socn_google inline_img %(common_class)' prov='Google' title='Google'></div>"],
	["Mailru","<div class='socn_mailru inline_img %(common_class)' prov='Mailru' title='MailRu'></div>"]
];
window.SOCBTN_LOGIN = [
	// +email
	["Facebook","<div class='inline_img socn_inline %(common_class)' prov='Facebook' title='Facebook'><img src='/img/share_ru/facebook_login.png'></div>"],
	// +email
	["Google","<div class='inline_img socn_inline %(common_class)' prov='Google' title='Google'><img src='/img/share_ru/google_login.png'></div>"+"<br>"],
	["Vkontakte","<div class='inline_img socn_inline %(common_class)' prov='Vkontakte' title='VKontakte'><img src='/img/share_ru/vkontakte.png'></div>"],
	["Odnoklassniki","<div class='inline_img socn_inline %(common_class)' prov='Odnoklassniki' title='Odnoklassniki'><img src='/img/share_ru/odnoklassniki.png'></div>"],
	// +email
	["Mailru","<div class='inline_img socn_inline %(common_class)' prov='Mailru' title='MailRu'><img src='/img/share_ru/moimir.png'></div>"]
];

window.init_lang = function(){
	var valid_socns = $._b("valid_social_networks");
	_s42_valids = [];
	for(var i=0;i<window.SOCBTN_SHARE42.length;i++){
		if(valid_socns.indexOf(window.SOCBTN_SHARE42[i][0]) >= 0){
			_s42_valids.push(window.SOCBTN_SHARE42[i]);
		}
	}
	window.SOCBTN_SHARE42 = _s42_valids;
	
	_lgn_valids = [];
	for(var i=0;i<window.SOCBTN_LOGIN.length;i++){
		if(valid_socns.indexOf(window.SOCBTN_LOGIN[i][0]) >= 0){
			_lgn_valids.push(window.SOCBTN_LOGIN[i]);
		}
	}
	window.SOCBTN_LOGIN = _lgn_valids;
	
	_pls_valids = [];
	for(var i=0;i<window.SOCBTN_SHAREPLUSO.length;i++){
		if(valid_socns.indexOf(window.SOCBTN_SHAREPLUSO[i]) >= 0){
			_pls_valids.push(window.SOCBTN_SHAREPLUSO[i]);
		}
	}
	window.SOCBTN_SHAREPLUSO = _pls_valids;
};
init_lang();

head.js(
	"http://static.gamerotor.com/scripts/sites/jquery/jquery.lightbox_me.js"
	,function(){
		window.FLAG_ADVANCEDJS_LOADED = 1;
	}
);

var jsonRqType = "json";
if ( !$.browser.msie ) {// Fuck that, thats why
	head.js(
		"http://static.gamerotor.com/scripts/sites/jquery/jquery.noty.js"
		,"http://static.gamerotor.com/scripts/sites/jquery/jquery.noty.top.js"
		,"http://static.gamerotor.com/scripts/sites/jquery/jquery.noty.inline.js"
		,"http://static.gamerotor.com/scripts/sites/jquery/jquery.noty.default.js"
	);
}else{
	jsonRqType = "jsonp";
};

window.jq_is_emailok = function (emailaddressVal) {
	if(core_len(emailaddressVal)<=3){
		return false;
	}
	if(emailaddressVal.indexOf(window.CONST_GUEST_PREFIX) >= 0){
		return true;
	}
	var emailReg = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,10}$/;
	if(!emailReg.test(emailaddressVal)) {
		return false;
	}
	return true;
}

window.jq_statHitPage = function(page_name,page_details) {
	var iframe_referrer = core_coalesce($.Storage.get(window.CONST_JSSTORE_REFER),'');
	if(core_len(iframe_referrer) == 0){
		if(window.bootstrap_config && window.bootstrap_config['referrer'] != null && window.bootstrap_config['referrer'].indexOf("none") < 0){
			iframe_referrer = "url_"+encodeURIComponent(window.bootstrap_config['referrer']);
		}else{
			iframe_referrer = "direct";
		}
	}
	var hiturl = page_name+"/ref_"+iframe_referrer;
	if(page_details != null){
		hiturl = hiturl+"/"+page_details;
	}
	jq_statHit({page:hiturl});
}

window.jq_show_noty = function(msg_id) {
	if(msg_id == null){
		if($.noty != null){
			$.noty.closeAll();
		}
		return;
	}
	if($.noty == null){
		// not yet
		alert(msg_id);
		return;
	}
	var confa = {
			text: msg_id,
			timeout: 15000,
			type: 'warning',
			dismissQueue: true,
			closeWith: ['click'],
			template: '<div class="noty_message"><span class="noty_text"></span><div class="noty_close"></div></div>',
		};
	if($('#gr_notyblock').length>0){
		$('#gr_notyblock').show();
		confa.layout = "inline";
		$('#gr_notyblock').noty(confa);
	}else{
		noty(confa);
	}
}

window.jq_lightbox_me_simplified_ids = [];
window.jq_lightbox_me = function(selector,params) {
	if(window.jq_lightbox_me_simplified_ids.indexOf(selector) >= 0){
		if(params){
			$(selector).show();
		}else{
			$(selector).hide();
		}
		return;
	}
	if($(selector).lightbox_me == null){
		if(params){
			core_log("jq_lightbox_me: lightbox not loaded, showing selector="+selector);
			$(selector).show();
		}else{
			core_log("jq_lightbox_me: lightbox not loaded, hiding selector="+selector);
			$(selector).hide();
		}
		return;
	}
	if(params){
		core_log("jq_lightbox_me: lightbox, showing selector="+selector);
		params.zIndex = window.CONST_ZINDEX_LOGIN;
		params.showOverlay = (params.overlayCSS == null)?false:true;
		if(params.closeClick == null){
			params.closeClick = true;
		}
		$(selector).lightbox_me(params);
	}else{
		core_log("jq_lightbox_me: lightbox, hiding selector="+selector);
		$(selector).hide();
		$(selector).trigger("close");
	}
}

// Preloading images
var js_const_inprogress = "loading";
var js_images_loaded = {loading: 0};
window.jq_preloadimages = function(img_array_raw,onOk) {
	var i = 0;
	var img_arr = [];
	for(i=0;i<img_array_raw.length;i++){
		if(core_len(img_array_raw[i])>0 && js_images_loaded[img_array_raw[i]] == null){
			js_images_loaded[img_array_raw[i]] = js_const_inprogress;
			img_arr.push(img_array_raw[i]);
		}
	}
	var max_imgs2wait = img_arr.length;
	for(i=0;i<img_arr.length;i++){
		var img_src = img_arr[i];
		var img_jq = $('<img />');
		js_images_loaded[js_const_inprogress]++;
		img_jq.attr('src', img_src).load(function(evn){
			js_images_loaded[js_const_inprogress]--;
			var loaded_src = $(this).attr('src');
			core_log("Image loaded:"+loaded_src);
			js_images_loaded[loaded_src] = this;
			max_imgs2wait--;
			if(max_imgs2wait == 0){
				max_imgs2wait = -1;
				if(onOk != null){
					onOk();
				}
			}
		});
	}
}

window.jq_setdiv_bgimage = function(div_jqo,url_bg, ovl)
{
	if(div_jqo == null || div_jqo.length == 0){
		// something wrong.. dom fucked?
		return;
	}
	// ww hh
	var ww = parseInt(core_getinstring(url_bg,"_ww","_"));
	var hh = parseInt(core_getinstring(url_bg,"_hh"));
	if(ww != 0 && hh != 0){
		div_jqo.css({
			width: ww+"px",
			height: hh+"px"
		});
	}
	if(ovl != null){
		ovl.ww = ww;
		ovl.hh = hh;
	}
	// In case of presetted bg skipping step to avoid flickering
	if(core_coalesce(div_jqo.css('background'),"").indexOf(url_bg) < 0){
		div_jqo.css({
			background: "url("+url_bg+") no-repeat"
		});
		//core_log("Button bg changed to "+url_bg);
	}
}

// button generation, should be applied to elements like <a><img></a>
window.jq_createButton = function(div_selector, ovl) {
	if($(div_selector).length == 0){
		return;
	}
	jq_preloadimages([ovl.url_hover, ovl.url_bg]);
	$(div_selector).css({
		display: "inline-block",
		position: "relative",
		"text-align": "center"
	});
	$(div_selector).css({
		cursor: "hand",
		cursor: "pointer"
	});
	$(div_selector).hover(
		function() {
			if(core_len(ovl.url_hover)>0 && js_images_loaded[js_const_inprogress] == 0){
				jq_setdiv_bgimage($(this),ovl.url_hover);
			}
		}, function(){
			if(js_images_loaded[js_const_inprogress] == 0){
				jq_setdiv_bgimage($(this),ovl.url_bg);
			}
		});
	$(div_selector).click(function(e) { ovl.onClick(); e.preventDefault(); });
	if(ovl.ww == null){
		ovl.ww = $(div_selector).width();
	}
	if(ovl.hh == null){
		ovl.hh = $(div_selector).height();
	}
	jq_setdiv_bgimage($(div_selector), ovl.url_bg, ovl);
	$(div_selector+" img").hide();
	$(div_selector).addClass("ui_button_label");
	$(div_selector+" span").css({
		position: "relative",
		"line-height": ovl.hh+"px"
	});
}

// login/register form
jq_preloadimages(["/img/bt_green_2_ww158_hh42.png","/img/bt_green_1_ww150_hh50.png","/img/bg_rega_popup_ww603_hh380.png","/img/bg_login_popup2_ww250_hh250.png"]);
var is_already_open = 0;
window.jq_prepare_ui = function() {
	if($('#gr_enterdialog_bg').length==0){
		if(window.gr_enterdialog_bg_style == null){
			window.gr_enterdialog_bg_style = 'position: absolute; left: 30%; top: 30%; z-index: '+(window.CONST_ZINDEX_LOGIN)+';';
		}
		if(window.gr_enterdialog_bg_parent == null){
			window.gr_enterdialog_bg_parent = 'body';
		}else{
			jq_lightbox_me_simplified_ids.push('#gr_enterdialog_bg');
		}
		var newdiv = $('<div id="gr_enterdialog_bg" style="background:url(/img/bg_login_popup2_ww250_hh250.png) no-repeat; width:250px; height:250px;  display:none;"'+window.gr_enterdialog_bg_style+'/>');
		$(window.gr_enterdialog_bg_parent).append(newdiv);
		
		var newdiv3 = $('<div id="gr_pleasewait" style="background:url(/img/bg_rega_block_ww250_hh80.png) no-repeat; position: absolute; width:250px; height:80px; left: 65%; top: 20%; z-index: '+(window.CONST_ZINDEX_LOGIN+20)+'; display:none;"><div style="padding:30px 40px 0px 40px;text-align:center;">'+$._b("Connecting to server")+'</div></div>');
		$('body').append(newdiv3);
		
		var newdiv4 = $('<div id="gr_notyblock" style="position: absolute; width:40%; height:100px; left: 30%; top: 5%; z-index: '+(window.CONST_ZINDEX_LOGIN+30)+'; display:none;"></div>');
		$('body').append(newdiv4);
	}else{
		// Closing previous
		jq_lightbox_me('#gr_enterdialog_bg');
	}
}

window.jq_ui_popupLoginForm = function(overloads) {
	jq_prepare_ui();
	core_log("jq_ui_popupLoginForm: starting");
	is_already_open = is_already_open+1;
	jq_lightbox_me('#gr_enterdialog_bg',{
			overlayCSS:null, //{background: 'black', opacity: .1},
			centered:false,
			modalCSS:{top: '30%', left: '70%'} ,
			closeClick:false,
			onClose: function(){
				is_already_open = is_already_open-1;
			}
		});
	
	//onLoad: function() { $('#sign_up').find('input:first').focus() }
	var mode = 1; // registration
	if(overloads.mode != null){
		mode = overloads.mode;
	}
	overloads.mode = mode;
	var form_html = "<center>";
	if(mode == window.CONST_MODE_VIASNLGN){
		jq_setdiv_bgimage($('#gr_enterdialog_bg'),"/img/bg_login_popup2_ww250_hh250.png");
		form_html += "<table cellspacing='0' cellpadding='0' border='0' class='ui_form' style='padding:20px 20px 20px 20px;'>";
		form_html += "<form action='#' method='get' id='gr_form_login'>";
		var socn_buttons = get_socialbuttons(true);
		form_html += "<tr><td colspan='2' align='center' valign='top'><span style='vertical-align:top;'>"+$._b("Use social login")+":</span><br><br>"
		form_html += socn_buttons+"</div></td></tr>";
		//form_html += "<tr><td colspan='2' align='center' valign='top'>";
		//form_html += "<a id='gr_form_switch' to_mode='"+window.CONST_MODE_REG+"'><img src='/img/bt_green_2_ww158_hh42.png' src2='/img/bt_green_2_ovl.png'/><span>"+$._b("REGISTER")+"</span></a>";
		//form_html += "</td></tr>";
		form_html += "</form>";
		form_html += "</table>";
	}
	if(mode == window.CONST_MODE_REG){
		jq_setdiv_bgimage($('#gr_enterdialog_bg'),"/img/bg_rega_popup_ww603_hh380.png");
		form_html += "<table cellspacing='0' cellpadding='0' border='0' class='ui_form' style='padding-top:60px;'>";
		form_html += "<form action='#' method='get' id='gr_form_rega'>";
		form_html += "<input type='hidden' id='rgf_ppic'>";
        form_html += "<tr><td class='ui_form_lbl'>"+$._b("Your name")+":</td><td class='ui_form_inp'><input type='text' id='rgf_name' maxlength='40'></td></tr>";
		form_html += "<tr><td class='ui_form_lbl'>"+$._b("Email")+"*:</td><td class='ui_form_inp'><input type='text' id='rgf_email' maxlength='40'></td></tr>";
		form_html += "<tr class='fld_psw'><td class='ui_form_lbl'>"+$._b("Password")+"*:</td>";
		form_html += "<td class='ui_form_inp'><input type='password' id='rgf_password' maxlength='40'></td></tr>";
		form_html += "<tr class='fld_psw'><td class='ui_form_lbl'>"+$._b("Retype password")+"*:</td>";
		form_html += "<td class='ui_form_inp'><input type='password' id='rgf_password2' maxlength='40'></td></tr>";
		form_html += "<tr><td colspan='2' align='center' valign='top'>";
		form_html += "<a id='gr_form_switch' to_mode='"+window.CONST_MODE_LGN+"'><img src='/img/bt_green_2_ww158_hh42.png' src2='/img/bt_green_2_ovl.png'/><span>"+$._b("LOGIN")+"</span></a>";
		form_html += "<a id='gr_form_rega_submit' href='javascript:jq_login({mode: "+window.CONST_MODE_REG+"});'><img src='/img/bt_green_1_ww150_hh50.png' src2='/img/bt_green_1_ovl.png'/><span>"+$._b("PLAY")+"</span></a>";
		form_html += "</td></tr>";
		form_html += "<tr><td colspan='2' align='center'><div class='ui_small_text' style='width:380px;'>"+$._b("REGISTRATION_TERMS")+"</div>";
		form_html += "</td></tr>";
		form_html += "</form>";
		form_html += "</table>";
	}
	if(mode == window.CONST_MODE_LGN){
		jq_setdiv_bgimage($('#gr_enterdialog_bg'),"/img/bg_login_popup_ww603_hh266.png");
		form_html += "<table cellspacing='0' cellpadding='0' border='0' class='ui_form' style='padding-top:60px;'>";
		form_html += "<form action='#' method='get' id='gr_form_login'>";
		form_html += "<tr><td class='ui_form_lbl'>"+$._b("Email")+"*:</td><td class='ui_form_inp'><input type='text' id='rgf_email' maxlength='40'></td></tr>";
		form_html += "<tr><td class='ui_form_lbl'>"+$._b("Password")+"*:</td><td class='ui_form_inp'><input type='password' id='rgf_password' maxlength='40'><a href='#' id='gr_form_switch2fgp' class='ui_small_text' style='position:relative;left: 20px;'>"+$._b("Forgot password?")+"</td></tr>";
		form_html += "<tr><td colspan='2' align='center' valign='top'>";
		form_html += "<a id='gr_form_switch' to_mode='"+window.CONST_MODE_VIASNLGN+"'><img src='/img/bt_green_2_ww158_hh42.png' src2='/img/bt_green_2_ovl.png'/><span>"+$._b("LOGIN_SOC")+"</span></a>";
		form_html += "<a id='gr_form_login_submit' href='javascript:jq_login({mode: "+window.CONST_MODE_LGN+"});'><img src='/img/bt_green_1_ww150_hh50.png' src2='/img/bt_green_1_ovl.png'/><span>"+$._b("PLAY")+"</span></a>";
		form_html += "</td></tr>";
		form_html += "</form>";
		form_html += "</table>";
	}
	if(mode == window.CONST_MODE_FGP){
		jq_setdiv_bgimage($('#gr_enterdialog_bg'),"/img/bg_login_popup_ww603_hh266.png");
		form_html += "<table cellspacing='0' cellpadding='0' border='0' class='ui_form' style='padding-top:60px;'>";
		form_html += "<form action='#' method='get' id='gr_form_fgp'>";
		form_html += "<tr><td class='ui_form_lbl'>"+$._b("Email")+"*:</td><td class='ui_form_inp'><input type='text' id='rgf_email' maxlength='40'></td></tr>";
		form_html += "<tr><td colspan='2' align='center' valign='top'>";
		form_html += "<a id='gr_form_switch'><img src='/img/bt_green_2_ww158_hh42.png' src2='/img/bt_green_2_ovl.png'/><span>"+$._b("LOGIN")+"</span></a>";
		form_html += "<a href='javascript:jq_login({mode: "+window.CONST_MODE_FGP+"});' id='gr_form_fgp_submit'><img src='/img/bt_green_1_ww150_hh50.png' src2='/img/bt_green_1_ovl.png'/><span>"+$._b("REMIND")+"</span></a>";
		form_html += "</td></tr>";
		form_html += "</form>";
		form_html += "</table>";
	}
	form_html += "</center>";
	$('#gr_enterdialog_bg').html(form_html);
	
	var gr_def_email = $.Storage.get(window.CONST_JSSTORE_EMAIL);
	if(core_len(gr_def_email)>0){
		$('#rgf_email').val(gr_def_email);
	}
	$('#gr_form_switch2fgp').click(function(){
		overloads.mode = 2;
		jq_ui_popupLoginForm(overloads);
	})
	jq_createButton("#gr_form_switch",{
		url_bg: $("#gr_form_switch img").attr('src')
		,url_hover: $("#gr_form_switch img").attr('src2')
		,onClick:function(){
			jq_show_noty(null);
			overloads.mode = parseInt($("#gr_form_switch").attr('to_mode'));
			jq_ui_popupLoginForm(overloads);
			return false;
		}
	});
	jq_createButton("#gr_form_login_submit",{
		url_bg: $("#gr_form_login_submit img").attr('src')
		,url_hover: $("#gr_form_login_submit img").attr('src2')
		,onClick:function(){
			var email = core_coalesce($('#rgf_email').val(),'');
			var psw = $('#rgf_password').val();
			email = email.toLowerCase();
			if(!jq_is_emailok(email)){
				$('#rgf_email').focus();
				jq_show_noty($._b('Please enter valid email address'));
				return false;
			}
			if(core_len(psw) < 3){
				$('#rgf_password').focus();
				jq_show_noty($._b('Password must be at lease 3 characters in length'));
				return false;
			}
			jq_login({mode:window.CONST_MODE_LGN
				,email:email
				,password:psw
				,target_widget:overloads.target_widget});
			return false;
		}
	});
	jq_createButton("#gr_form_rega_submit",{
		url_bg: $("#gr_form_rega_submit img").attr('src')
		,url_hover: $("#gr_form_rega_submit img").attr('src2')
		,onClick:function(){
			var username = $('#rgf_name').val();
			var email = core_coalesce($('#rgf_email').val(),'');
			var psw = $('#rgf_password').val();
			var psw2 = $('#rgf_password2').val();
			email = email.toLowerCase();
			if(!jq_is_emailok(email)){
				$('#rgf_email').focus();
				jq_show_noty($._b('Please enter valid email address'));
				return false;
			}
			if(core_len(psw) < 3){
				$('#rgf_password').focus();
				jq_show_noty($._b('Password must be at lease 3 characters in length'));
				return false;
			}
			if(psw != psw2){
				$('#rgf_password').focus();
				jq_show_noty($._b('Passwords did not match'));
				return false;
			}
			if(core_len(username) <= 1){
				username = core_getinstring(email,null,"@");
			}
			if(core_len(username) <= 1){
				$('#rgf_name').focus();
				jq_show_noty($._b('Please enter your name'));
				return false;
			}
			jq_login({mode:window.CONST_MODE_REG
				,username:username
				,email:email
				,password:psw
				,target_widget:overloads.target_widget});
			return false;
		}
	});
	jq_createButton("#gr_form_fgp_submit",{
		url_bg: $("#gr_form_fgp_submit img").attr('src')
		,url_hover: $("#gr_form_fgp_submit img").attr('src2')
		,onClick:function(){
			var email = core_coalesce($('#rgf_email').val(),'');
			email = email.toLowerCase();
			if(!jq_is_emailok(email)){
				$('#rgf_email').focus();
				jq_show_noty($._b('Please enter valid email address'));
				return false;
			}
			jq_login({mode:window.CONST_MODE_FGP
				,email:email
				,target_widget:overloads.target_widget});
			return false;
		}
	});
	$("#rgf_password").keypress(function(event) {
		if (event.which == 13) {
			event.preventDefault();
			$("#gr_form_login_submit").click();
			$("#gr_form_rega_submit").click();
		}
	});
	$("#rgf_password2").keypress(function(event) {
		if (event.which == 13) {
			event.preventDefault();
			$("#gr_form_login_submit").click();
			$("#gr_form_rega_submit").click();
		}
	});
	$("#rgf_email").keypress(function(event) {
		if (event.which == 13) {
			event.preventDefault();
			$("#gr_form_login_submit").click();
			$("#gr_form_rega_submit").click();
			$("#gr_form_fgp_submit").click();
		}
	});
	$('.socn_bt').click(function(){
		var prov = $(this).attr("prov");
		overloads.mode = window.CONST_MODE_VIASNLGN;
		overloads.socn_do_redir = $(this).attr("do_redir");
		jq_statHitPage("login_viasn/"+prov);
		jq_login_viasn(prov,overloads)
	});
}


// Auth checks, registration, etc
window.jq_auto_rega = function(overloads) {
	jq_prepare_ui();
	jq_statHitPage("rega_auto");
	var randomnames = $._b("RANDOM_NAMES");
	randomnames_arr = randomnames.split("|");
	var randomnames_ind = parseInt(Math.random()*randomnames_arr.length);
	var username = core_trim(randomnames_arr[randomnames_ind]);
	var now = new Date();
	var email = window.CONST_GUEST_PREFIX+":"+core_padstring(now.getDate(),2)+core_padstring(now.getMonth(),2)+core_padstring(now.getFullYear(),4)+"_"+parseInt(1000+Math.random()*999)+"_"+parseInt(1000+Math.random()*999);
	var psw = window.CONST_GUEST_PSW;
	jq_login({mode:window.CONST_MODE_REG
		,username:username
		,email:email
		,password:psw
		,viasn:""
		,ppic:""
		,flags: ""
		,target_widget:overloads.target_widget});
}

window.jq_login = function(overloads) {
	var api_url = $._conf("api_url");
	var mode = core_coalesce(overloads.mode,0);
	jq_statHit({page:"action/jq_login"+mode});
	core_log("jq_login",overloads);
	if(mode == window.CONST_MODE_WIDGETLGN){
		var stored_auth = $.Storage.get(window.CONST_JSSTORE_AUTH);
		overloads.auth = core_coalesce(overloads.auth,stored_auth);
		if(core_len(overloads.auth) == 0){
			return false;
		}
	}
	//core_log_stacktrace("jq_login");
	//$.support.cors = true;// via transport!
	if(mode == window.CONST_MODE_REG || mode == window.CONST_MODE_VIASNLGN){
		overloads.email = core_coalesce(overloads.email,"");
		if(mode == window.CONST_MODE_REG){
			if(core_len(overloads.email) == 0){
				// In case of registering via semi-viasn
				overloads.email = $('#rgf_email').val();
			}
			overloads.password = core_coalesce(overloads.password,$('#rgf_password').val());
			if(core_len(overloads.password) > 0){
				// Not a viasn, clearing data
				overloads.viasn = null;
			}
		}
		var socn_jsoned = overloads.viasn;
		overloads.username = core_coalesce(overloads.username,$('#rgf_name').val());
		overloads.ppic = core_coalesce(overloads.ppic,$('#rgf_ppic').val());
		overloads.flags = core_coalesce(overloads.flags,"");
		if(core_len(overloads.email) == 0){
			if(core_len(socn_jsoned) == 0){
				return false;
			}
			overloads.email = "";
		}
		if(core_len(overloads.username) == 0){
			return false;
		}
		if(core_len(overloads.password) == 0){
			if(core_len(socn_jsoned) == 0){
				return false;
			}
			overloads.password = "";
		}
		var userLang = window.jq_detectLang(false);// (navigator.language) ? navigator.language : navigator.userLanguage; 
 		var command_data = {
				username: escape(overloads.username),
				email: escape(overloads.email),
				password: escape(overloads.password),
				ppic: encodeURIComponent(overloads.ppic),
				lang: userLang,
				flags: overloads.flags,
				viasn: socn_jsoned
			};
		var command_name = "register";
		if(mode == window.CONST_MODE_VIASNLGN){
			command_name = "viasnlogin";
		}
		var fvis = core_coalesce($.Storage.get(window.CONST_JSSTORE_REFER),'');
		if(core_len(fvis)>0){
			command_data.referrer = fvis;
		}
		var fvis_url = core_coalesce($.Storage.get(window.CONST_JSSTORE_REFERURL),'');
		if(core_len(fvis_url)>0){
			command_data.referrer_origin = fvis_url;
		}
		jq_lightbox_me('#gr_pleasewait',{
			overlayCSS:{background: 'black', opacity: .5},
			centered:true,
			closeClick:false,
			closeEsc:false,
			overlaySpeed:0,
			lightboxSpeed:0});
		// Sending request
		$.ajax({
			url: $._conf("api_url")+command_name,
			data: command_data,
			dataType: jsonRqType,
			type: 'post',
			async: true,
			crossDomain: true,
			success: function(json_response, textStatus, xhr) {
				core_log("jq_login: registration json_response",json_response);
				jq_lightbox_me('#gr_pleasewait',null);
				if(core_coalesce(json_response.error_code,0) < 0){
					jq_show_noty($._b("ERROR_SERVER_FAILURE")+": "+json_response.error_code);
					return;
				}
				// if(core_len(json_response.uid) == 0 && core_coalesce(json_response.reason,0) == -150/-151???){ // API_ERR_WRONG_USER
					// // email is in use, trying to login
					// if(core_len(socn_jsoned)>0){
						// overloads.viasn = socn_jsoned;
						// overloads.mode = window.CONST_MODE_LGN;
						// jq_login(overloads);
						// return;
					// }
				// }
				if(core_len(json_response.uid) == 0){
					jq_show_noty($._b("ERROR_REGISTRATION_EMAILINUSE"));
					return;
				}
				$.Storage.set(window.CONST_JSSTORE_REGOK,"1");
				$.Storage.set(window.CONST_JSSTORE_EMAIL,overloads.email);
				//logging user
				var postreg_ovl = {mode:window.CONST_MODE_LGN
					,uid:json_response.uid
					,password:overloads.password
					,target_widget:overloads.target_widget};
				if(mode == window.CONST_MODE_VIASNLGN){
					postreg_ovl.viasn = socn_jsoned;
				}
				jq_login(postreg_ovl);
				return;
			},
			error: function(xhr, textStatus, errorThrown) {
				jq_lightbox_me('#gr_pleasewait',null);
				core_log("jq_login: registration error: '"+textStatus+"'/'"+errorThrown+"'");
				jq_show_noty($._b("ERROR_SERVER_FAILURE")+": Error 503");
			}
		});
		return true;
	}
	if(mode == window.CONST_MODE_LGN){
		overloads.uid = core_coalesce(overloads.uid,"");
		overloads.email = core_coalesce(overloads.email,"");
		if(core_len(overloads.email) == 0){
			// In case of registering via semi-viasn
			overloads.email = $('#rgf_email').val();
		}
		overloads.password = core_coalesce(overloads.password,$('#rgf_password').val());
		if(core_len(overloads.password) > 0){
			// Not a viasn, clearing data
			overloads.viasn = null;
		}
		var socn_jsoned = overloads.viasn;
		if(core_len(overloads.uid) == 0 && core_len(overloads.email) == 0 && core_len(socn_jsoned) == 0){
			core_log("jq_login: ignore, no uid");
			return false;
		}
		if(core_len(overloads.password) == 0 && core_len(socn_jsoned) == 0){
			core_log("jq_login: ignore, no password");
			return false;
		}
		if(core_len(overloads.target_widget) == 0){
			core_log("jq_login: ignore, no target_widget");
			return false;
		}
		var command_data = {
				widget: overloads.target_widget,
				uid: encodeURIComponent(overloads.uid),
				email: escape(overloads.email),
				password: escape(overloads.password),
				viasn: socn_jsoned
			};
		// Sending request
		jq_show_noty(null);
		jq_lightbox_me('#gr_pleasewait',{
			overlayCSS:{background: 'black', opacity: .5},
			centered:true,
			closeClick:false,
			closeEsc:false,
			overlaySpeed:0,
			lightboxSpeed:0});
		$.ajax({
			url: $._conf("api_url")+"login",
			data: command_data,
			dataType: jsonRqType,
			type: 'post',
			async: true,
			crossDomain: true,
			success: function(json_response, textStatus, xhr) {
				core_log("jq_login: json_response",json_response);
				jq_lightbox_me('#gr_pleasewait',null);
				if(core_coalesce(json_response.error_code,0) < 0){
					jq_show_noty($._b("ERROR_SERVER_FAILURE")+": "+json_response.error_code);
					return;
				}
				if(core_len(json_response.auth) == 0){
					jq_show_noty($._b("ERROR_USER_NOTFOUND"));
					return;
				}
				core_log("jq_login: user logged:"+json_response.auth);
				$.Storage.set(window.CONST_JSSTORE_EMAIL,overloads.email);
				$.Storage.set(window.CONST_JSSTORE_AUTH,json_response.auth);
				// To escape iframes
				if(window.login_innewtab != null && window.login_innewtab > 0){
					overloads.force_newtab = window.login_innewtab;
					window.login_innewtab = null;
				}
				jq_redirect2page(overloads);
			},
			error: function(xhr, textStatus, errorThrown) {
				jq_lightbox_me('#gr_pleasewait',null);
				core_log("jq_login: login error: '"+textStatus+"'/'"+errorThrown+"'");
				jq_show_noty($._b("ERROR_SERVER_FAILURE")+": Error 503");
			}
		});
		return true;
	}
	if(mode == window.CONST_MODE_FGP){
		overloads.email = core_coalesce(overloads.email,$('#rgf_email').val());
		if(core_len(overloads.email) == 0){
			return false;
		}
		if(core_len(overloads.target_widget) == 0){
			return false;
		}
		var command_data = {
				email: escape(overloads.email),
				widget: encodeURIComponent(overloads.target_widget),
			};
		// Sending request
		$.ajax({
			url: $._conf("api_url")+"remind_psw",
			data: command_data,
			dataType: jsonRqType,
			type: 'post',
			async: true,
			crossDomain: true,
			success: function(json_response, textStatus, xhr) {
				if(core_coalesce(json_response.error_code,0) < 0){
					jq_show_noty($._b("ERROR_SERVER_FAILURE")+": "+json_response.error_code);
					return;
				}
				if(core_coalesce(json_response.reminded,'0') != '1'){
					jq_show_noty($._b("ERROR_USER_NOTFOUND"));
					return;
				}
				jq_show_noty($._b("Password was sent to your address"));
				overloads.mode = window.CONST_MODE_LGN;
				jq_ui_popupLoginForm(overloads);
			},
			error: function(xhr, textStatus, errorThrown) {
				jq_show_noty($._b("ERROR_SERVER_FAILURE")+": Error 503");
			}
		});
		return true;
	}
	return false;
}

window.viasn_popup = null;
window.viasn_overloads = null;
window.jq_open_hybridauth = function(provider){
	var wnd = window.open(window.CONST_HYBRIDAUTH_URL+provider+"&ie9stub="+escape("http://static.gamerotor.com/scripts/sites/iframe_cb.html"),"grlogin","width=750,height=500,left=200,top=120");
	wnd.focus();
	return wnd;
}
window.jq_login_viasn = function(provider,overloads) {
	$.Storage.set(window.CONST_JSSTORE_SOCNLA,provider);
	if(overloads.socn_do_redir != null && overloads.socn_do_redir == "yes"){
		// Redirect to soc_install
		var target_urls = $._conf("widget_urls");
		var target_url_soc = ""+target_urls[overloads.target_widget]["soc_install_"+provider];
		core_log("jq_login_viasn target_url_soc for "+provider,target_url_soc);
		if(target_url_soc != null){
			document.location.href = target_url_soc;
		}
		return;
	}
	window.viasn_overloads = overloads;
	window.viasn_overloads.last_provider = provider;
	window.viasn_popup = jq_open_hybridauth(provider);
}

window.jq_login_viasn_callback = function(provider_data) {
	if(window.viasn_popup != null){
		window.viasn_popup.close();
		window.viasn_popup = null;
	}
	core_log("jq_login_viasn_callback:",[provider_data,window.viasn_overloads]);
	if(window.viasn_overloads != null){
		overloads = window.viasn_overloads;
		jq_statHit({page:"action/jq_login_viasn/"+overloads.last_provider});
		var socn_jsoned = $.toJSON(provider_data.profile);
		overloads.viasn = socn_jsoned;
		overloads.email = null;// Resetting from previous rounds
		if(overloads.mode == window.CONST_MODE_LGN){
			if(core_len(provider_data.profile.email) > 0){
				$('#rgf_email').val(provider_data.profile.email);
				overloads.email = provider_data.profile.email;
			}
			jq_login(overloads);
		}
		if(overloads.mode == window.CONST_MODE_REG){
			overloads.ppic = provider_data.profile.photoURL;
			$('#rgf_ppic').val(overloads.ppic);
			overloads.username = core_coalesce(provider_data.profile.displayName,window.CONST_GUEST_PREFIX);
			$('#rgf_name').val(overloads.username);
			if(core_len(provider_data.profile.email) > 0){
				$('#rgf_email').val(provider_data.profile.email);
				overloads.email = provider_data.profile.email;
			}else {
				if(core_len($('#rgf_email').val()) == 0){
					$('#rgf_email').focus();
					$('.fld_psw').hide();
					jq_show_noty($._b("Please enter your email address to continue"));
					return;
				}
				overloads.email = $('#rgf_email').val();
			}
			jq_login(overloads);
		}
		if(overloads.mode == window.CONST_MODE_VIASNLGN){
			if(provider_data.profile == null){
				provider_data.profile = {};
			}
			overloads.ppic = provider_data.profile.photoURL;
			overloads.username = core_coalesce(provider_data.profile.displayName,window.CONST_GUEST_PREFIX);
			//overloads.flags
			overloads.last_provider = core_coalesce(overloads.last_provider,"unknown");
			provider_data.profile.identifier = core_coalesce(provider_data.profile.identifier,"");
			if(core_len(provider_data.profile.email) > 0){
				overloads.email = provider_data.profile.email;
			}else{
				overloads.email = window.CONST_GUEST_PREFIX+":"+overloads.last_provider+":"+provider_data.profile.identifier
			}
			//core_log("jq_login_viasn_callback: overloads",overloads);
			if(core_len(overloads.username) == 0 || core_len(provider_data.profile.identifier) == 0){
				jq_statHitPage("login_viasn/"+overloads.last_provider+"_error");
				jq_show_noty($._b("This social network is not accessible now"));
				return;
			}
			jq_login(overloads);
		}
	}
}

window.jq_resetauth = function() {
	$.Storage.set(window.CONST_JSSTORE_AUTH,"");
}

window.jq_logout_user_ask = function(focus_widget, user_uid) {
	var userinfo = rqw_getcacheduser(user_uid);
	if(userinfo != null && (userinfo.u_flags & window.FLAGS_USER_SOCPRESENT) == 0){
		if(confirm($._b("Do you want to add social network to your profile before logging off"))){
			jq_redirect2page({target_widget:focus_widget},"profile_edit");
			return;
		}
	}
	jq_logout_user(focus_widget);
}

window.jq_logout_user = function(focus_widget) {
	jq_resetauth();
	jq_redirect2login({target_widget: focus_widget});
}

window.jq_redirect2login = function(overloads) {
	return window.jq_redirect2page(overloads,"login");
}

window.jq_redirect2page = function(overloads,redir_kind,additional_pars) {
	core_log("jq_redirect2page",[overloads,redir_kind,additional_pars]);
	if(core_len(overloads.target_widget) == 0){
		return false;
	}
	if(redir_kind == null){
		redir_kind = "game";
	}
	var target_urls = $._conf("widget_urls");
	var target_url = ""+target_urls[overloads.target_widget][redir_kind];
	if(core_len(target_url)>0){
		if(additional_pars != null){
			for(var pp in additional_pars){
				if(target_url.indexOf("%("+pp+")")>=0){
					target_url = core_str_replace(target_url,"%("+pp+")",additional_pars[pp]);
				}else{
					if(target_url.indexOf("?")>=0){
						target_url+="&";
					}else{
						target_url+="?";
					}
					target_url += pp + "=" + additional_pars[pp];
				}
			}
		}
		if(overloads.force_newtab == 1){
			core_navigate_url_via_form(target_url, null,'GET','_blank');
			return true;
		}
		if(overloads.force_newtab == 2){
			// escaping iframe by reloading parent
			//window.open(target_url, '_newtab');
			core_navigate_url_via_form(target_url, null,'GET','_parent');
			return true;
		}
		document.location.href = target_url;
		return true;
	}
	return false;
}

window.jq_check_friendinvites = function(dopush) {
	if(dopush){
		var invby = $.Storage.get(window.CONST_JSSTORE_INVBY);
		if(core_len(invby) > 0){
			jq_query_api("add_friends"
				,{ user_ids: invby }
				,function(ok_answer){
					core_log("add_friends ok_answer",ok_answer);
				}
				,function(err_answer){
				});
			$.Storage.set(window.CONST_JSSTORE_INVBY,'');
		}
	}else{
		// Remebering any pending inviters
		var invby_url = $.url().param(window.CONST_JSSTORE_INVBY);
		if(core_len(invby_url) > 0){
			var cur_invby = core_coalesce($.Storage.get(window.CONST_JSSTORE_INVBY),'');
			if(cur_invby.indexOf(invby_url) < 0){
				if(core_len(cur_invby)>0){
					cur_invby = ","+cur_invby;
				}
				cur_invby = invby_url+cur_invby;
				$.Storage.set(window.CONST_JSSTORE_INVBY,cur_invby);
			}
		}
	}
	var referrer_type = core_coalesce($.Storage.get(window.CONST_JSSTORE_REFER),'');
	if(core_len(referrer_type) == 0){
		var fvis_url = $.url().param(window.CONST_JSSTORE_REFER);
		//core_log("CONST_JSSTORE_REFER:"+fvis_url);
		if(core_len(fvis_url) > 0){
			$.Storage.set(window.CONST_JSSTORE_REFER,fvis_url);
			//core_log("CONST_JSSTORE_REFER: installing: "+fvis_url);
		}
	}
	var refereurl = core_coalesce($.Storage.get(window.CONST_JSSTORE_REFERURL),'');
	//core_log("CONST_JSSTORE_REFERURL:"+refereurl);
	if(core_len(refereurl) == 0){
		refereurl = escape(document.location);// escape amust
		$.Storage.set(window.CONST_JSSTORE_REFERURL,refereurl);
		//core_log("CONST_JSSTORE_REFERURL: installing: "+refereurl);
	}
}

window.jq_query_api = function(meth,query_params,onOk,onFail) {
	if(!GamerotorServer.ready()){
		return;
	}
	var auth = $.Storage.get(window.CONST_JSSTORE_AUTH);
	return GamerotorServer.QueryApi(meth,query_params,auth,onOk,onFail);
}

window.jq_getInviteLink = function(focus_widget)
{
	var auth = $.Storage.get(window.CONST_JSSTORE_AUTH);
	var auth_pair = auth.split(":");
	if(core_len(auth_pair)<2){
		return;
	}
	var target_urls = $._conf("widget_urls");
	var invite_link = ""+target_urls[focus_widget]["invite"];
	invite_link = core_str_replace(invite_link,"%(uid)",auth_pair[0]);
	return invite_link;
}

window.jq_ui_ApiInvite = function(focus_widget,data)
{
	if(focus_widget == null){
		focus_widget = window.bootstrap_config['focus_widget'];
	}
	core_log("jq_ui_ApiInvite",[focus_widget,data]);
	var invite_link = jq_getInviteLink(focus_widget);
	var __header = $._b("Invite link")+":&nbsp;<input type='text' id='rgf_invitlink' maxlength='40' value='"+invite_link+"'>";
	data.__header = "";
	data.__header += "<tr><td align='center' valign='top' >"+__header+"</td></tr>";
	//data.__header += "<tr><td align='center' valign='top' class='ui_small_text' style='padding:0px 40px 7px 40px;'>"+$._b("Invite via social networks");
	data.__header += "</td></tr>";
	data.page_stat="invite"
	data.title = $._b("Invite Friends");
	jq_ui_ApiShare(focus_widget,data);
	jq_show_noty($._b("Invite via social networks"));
}

window.jq_bitly_url = function(url,onOk)
{
	var username="o_67f2rh0jue"; // bit.ly username
	var key="R_fa7171d8f461b3951151fa711fbc7589";
	$.ajax({
		url:"http://api.bit.ly/v3/shorten",
		data:{
			longUrl:url,
			apiKey:key,
			login:username,
			domain:"j.mp"},//bit.ly, j.mp, or bitly.com
		dataType:"jsonp",
		success:function(v)
		{
			var bit_url=v.data.url;
			onOk(bit_url);
		}
	});
}
window.jq_ui_ApiShare = function(focus_widget,data)
{
	// addthis?
	// bit.ly?
	// image crunching?
	core_log("jq_ui_ApiShare",[focus_widget,data]);
	if(focus_widget == null){
		jq_lightbox_me('#gr_sharedialog',null);
		return;
	}
	var invite_link = jq_getInviteLink(focus_widget);
	if($('#gr_sharedialog').length==0){
		var newdiv = $('<div id="gr_sharedialog" style="background:url(/img/bg_rega_popup_ww603_hh380.png) no-repeat; position: absolute; width:603px; height:380px; left: 25%; top: 20%; z-index: '+(window.CONST_ZINDEX_LOGIN)+'; display:none;"><center><div id="gr_enterdialog_title" style="background:url(/img/bg_title_ww272_hh45.png) no-repeat; width:272px; height:45px; padding-top:13px;"></div><div id="gr_sharedialog_content"></div></center></div>');
		$('body').append(newdiv);
	}
	$('#widget_canvas').css('visibility', 'hidden');
	is_already_open = is_already_open+1;
	jq_lightbox_me('#gr_sharedialog',{
		overlayCSS:{background: 'black', opacity: .5},
		centered:true,
		onClose: function(){
			is_already_open = is_already_open-1;
			$('#widget_canvas').css('visibility', 'visible');
		}
	});
	if(core_len(data.image)>0){
		invite_link += "&og_i="+encodeURIComponent(data.image);
	}
	if(core_len(data.title)>0){
		data.title = core_str_replace(data.title,"\"","'");
		data.title = core_str_replace(data.title,"\n"," ");
		data.title = core_str_replace(data.title,"  "," ");
		data.title = core_str_replace(data.title,"\r","");
		invite_link += "&og_t="+encodeURIComponent(data.title);
	}
	if(core_len(data.text)>0){
		data.text = core_str_replace(data.text,"\"","'");
		data.text = core_str_replace(data.text,"\n"," ");
		data.text = core_str_replace(data.text,"  "," ");
		data.text = core_str_replace(data.text,"\r","");
		invite_link += "&og_d="+encodeURIComponent(data.text);
	}
	invite_link_short = invite_link;
	core_log("jq_ui_ApiShare link: "+invite_link_short);
	data.page_stat = core_coalesce(data.page_stat,"share");
	jq_statHitPage(data.page_stat);
	$('#gr_sharedialog_content').html("<center><img src='http://lh5.googleusercontent.com/-l_WwKQnf2SQ/UF8LvCjtNyI/AAAAAAAAARg/YNAzjesuOlc/w497-h373/image_292913.gif' style='padding-top:50px;'></center>");
	// share42_modded: 
	// - lj is hidden
	// - separate url for odnoklassniki (short urls are prohibited)
	// - separate url for vk (short urls are not clickable)
	// - buttons have ids, to allow force-click on it
	//jq_bitly_url(invite_link,function(invite_link_short)
	invite_link_short = invite_link;
	{
		var form_html = "<center>";
		jq_setdiv_bgimage($('#gr_sharedialog'),"/img/bg_login_popup_ww603_hh266.png");
		form_html += "<table cellspacing='0' cellpadding='0' border='0' class='ui_form' style='padding-top:20px;'>";
		form_html += "<form action='#' method='get' id='gr_form_invit'>";
		if(core_len(data.title)>0){
			form_html += data.title+"<br>";
		}
		if(core_len(data.__header)>0){
			form_html += data.__header;
		}
		if(core_len(data.title)>0){
			//form_html += "<tr><td align='center' valign='top' >"+data.title+"</td></tr>";
			//$('#gr_enterdialog_title').html(data.title);
			$('#gr_enterdialog_title').html($._b("Invite link"));
		}
		form_html += "<tr><td align='center' valign='top' >"+$._b("Share via social networks")+"</td></tr>";
		form_html += "<tr><td align='center' valign='top'>";
		// old: share42
		//form_html += "<div class='share42init' data-url='"+invite_link_short+"' data-url2='"+invite_link+"' data-path='/img/share_ru/'";
		//if(core_len(data.title)>0){
		//	form_html += " data-title='"+data.title+"'";
		//}
		//form_html += "></div><scr"+"ipt type='text/javascript' src='/img/share_ru/share42_modded.js'></sc"+"ript>";
		// new: http://share.pluso.ru/
		form_html += '<scr'+'ipt type="text/javascript">(function() {'+
			'if (window.pluso)if (typeof window.pluso.start == "function") {window.pluso.start();return;}'+
			'if (window.ifpluso==undefined) { window.ifpluso = 1;'+
			'var d = document, s = d.createElement("script"), g = "getElementsByTagName";'+
			's.type = "text/javascript"; s.charset="UTF-8"; s.async = true;'+
			's.src = ("https:" == window.location.protocol ? "https" : "http")  + "://share.pluso.ru/pluso-like.js";'+
			'var h=d[g]("body")[0];'+
			'h.appendChild(s);'+
			'}})();</scr'+'ipt>'+
			'<div class="pluso" data-background="transparent" data-options="big,square,line,horizontal,nocounter,theme=01"'+
			'data-services="'+window.SOCBTN_SHAREPLUSO.join(",")+'"'+
			'data-url="'+invite_link_short+'"';
		if(core_len(data.title)>0){
			form_html += "data-title='"+data.title+"'";
		}
		form_html += '></div>';
		
		form_html += "</td></tr>";
		form_html += "<tr><td align='center' valign='top'><a href='javascript:jq_ui_ApiInvite(null,null);' id='gr_form_invit_submit'><img src='/img/bt_green_2_ww158_hh42.png' src2='/img/bt_green_2_ovl.png'/><span>"+$._b("CLOSE")+"</span></a>";
		form_html += "</td></tr>";
		form_html += "</form>";
		form_html += "</table>";
		form_html += "</center>";
		$('#gr_sharedialog_content').html(form_html);
		jq_createButton("#gr_form_invit_submit",{
			url_bg: $("#gr_form_invit_submit img").attr('src')
			,url_hover: $("#gr_form_invit_submit img").attr('src2')
			,onClick:function(){
				jq_ui_ApiShare(null,null);
				return false;
			}
		});
		if(window.share42updDOM){
			window.share42updDOM();
		}
		try{
			$('#rgf_invitlink').focus();
			setTimeout(function(){$('#rgf_invitlink').select();},100);
			// var provider = $.Storage.get(window.CONST_JSSTORE_SOCNLA);
			// for(var i=0;i<window.SOCBTN_SHARE42.length;i++){
				// if(window.SOCBTN_SHARE42[i][0] == provider){
					// var shbt = "sh42_bt"+window.SOCBTN_SHARE42[i][2];??? 2 not exist anymore
					// var elem = document.getElementById(shbt)
					// var res = core_SimulateEvent(elem,"click");
					// break;
				// }
			// }
		}catch(e){};
	}
	//);//jq_bitly_url
}

// required: head.js("https://secure.xsolla.com/paybar/jswidget/paybar.js");
window.jq_payment_email = '';
// iframe paystation?
// ping for payment success
var pingBalance_maxtry = 0;
var pingBalance_timeout = 0;
var pingBalance_widget = "";
var pingBalance_balancechange = -1;
var pingBalance_payOpts = {};
window.jq_ui_ApiPaymentCancel = function()
{
	core_log("jq_ui_ApiPaymentCancel");
	clearInterval(pingBalance_timeout);
	pingBalance_timeout = 0;
	pingBalance_maxtry = 0;
	$('#widget_canvas').css('visibility', 'visible');
	$("#widget_paybar").hide();
	$("#widget_paybar_paystation").hide();
}
window.jq_ui_ApiPaymentPingBalance = function()
{
	if(pingBalance_maxtry <= 0){
		jq_ui_ApiPaymentCancel();
		GamerotorServer.sendToClient({c: -1, m:'payFail'});
		return;
	}
	pingBalance_maxtry = pingBalance_maxtry-1;
	jq_query_api("balance"
		,{ widget: pingBalance_widget }
		,function(ok_answer){
			core_log("jq_ui_ApiPaymentPingBalance ok_answer",ok_answer);
			var change_ts = core_coalesce(ok_answer.change_ts,0);
			if(pingBalance_balancechange < 0){
				pingBalance_balancechange = ok_answer.change_ts;
			}
			if(change_ts != 0){
				if(pingBalance_balancechange != ok_answer.change_ts){
					pingBalance_balancechange = ok_answer.change_ts;
					GamerotorServer.sendToClient({c: -1, m:'paySuccess'});
					jq_ui_ApiPaymentCancel();
					try{
						// From https://secure.xsolla.com/paybar/jswidget/paybar.js
						$.fancybox.close();
						pingBalance_payOpts.service = core_coalesce(pingBalance_payOpts.service,0);
						jq_statHitPage("payment"+pingBalance_payOpts.service,"done");
					}catch(e){};
				}
			}
		}
		,function(err_answer){
			core_log("jq_ui_ApiPaymentPingBalance err_answer",err_answer);
			pingBalance_maxtry = 0;
		});
}

var xsolla_pb = true;
var userLang = window.jq_detectLang(false);
window.jq_ui_ApiPayment = function(focus_widget,data)
{
	core_log("jq_ui_ApiPayment",data);
	$('#widget_canvas').css('visibility', 'hidden');
	var req_v1 = data.user_id+"|"+data.service+"|"+((new Date()).getTime());
	pingBalance_payOpts = data;
	pingBalance_payOpts.service = core_coalesce(pingBalance_payOpts.service,0);
	jq_statHitPage("payment"+pingBalance_payOpts.service,"init");
	var req_price = data.price*1.0;// virtual to rub = 1;
	var info_text = $._b("Payment option");
	info_text = core_str_replace(info_text,"%(title)",data.title);
	$("#widget_paybar_info").html(info_text);
	if(xsolla_pb){
		$("#widget_paybar_content").show();
		var xsolla_pb_req = {
			element_id: 'widget_paybar_content',
			type: 'lightbox',
			project: $._conf("widget_urls")[focus_widget]["xsolla_id"],
			v1: req_v1,
			out: req_price,
			email: jq_payment_email,
			phone: '',
			local: userLang,
			template: { id: 'inline', icon_count: 7, other: true },
			errorCallback: function(message, category) { 
				jq_ui_ApiPaymentCancel();
				core_log('Payment error "' + message + '" at ' + category);
				GamerotorServer.sendToClient({c: -1, m:'paymentError'});
			},
		}
		window.xsolla_req = xsolla_pb_req;
		core_log("jq_ui_ApiPayment xsolla_req",window.xsolla_req);
		XPBWidget.init(window.xsolla_req);
	}else{
		$("#widget_paybar_paystation").show();
		var xsolla_ps_url = "https://secure.xsolla.com/paystation?projectid="+$._conf("widget_urls")[focus_widget]["xsolla_id"]+"&id_theme=34&local=ru&v1="+req_v1+"&email="+jq_payment_email+"&out="+req_price;
		core_log("jq_ui_ApiPayment xsolla_req",xsolla_ps_url);
		$("#widget_paybar_paystation").prop('src', xsolla_ps_url);
	}
	// Showing options and starting balance ping
	$("#widget_paybar").show();
	pingBalance_widget = focus_widget;
	pingBalance_maxtry = 100;
	pingBalance_timeout = window.setInterval(jq_ui_ApiPaymentPingBalance, 7000);
	core_log("jq_ui_ApiPayment balance ping #"+pingBalance_timeout);
}

window.get_socialbuttons = function(forlogin) {
	var common_class = "socn_bt";
	var all_socns = "";
	if(forlogin){
		for(var i=0;i<window.SOCBTN_LOGIN.length;i++){
			all_socns += window.SOCBTN_LOGIN[i][1];
		}
	}else{
		for(var i=0;i<window.SOCBTN_SHARE42.length;i++){
			all_socns += window.SOCBTN_SHARE42[i][1];
		}
	}
	all_socns = core_str_replace(all_socns,"%(common_class)",common_class);
	return all_socns;
}

window.show_legals = function() {
	$(document).ready(function(){
		var footer_html = $._b("LEGAL_SITE_TERMS");
		var langs = jq_getLangs();
		for(var li=0;li<langs.length;li++){
			var lmlng = langs[li];
			footer_html += "&nbsp;|&nbsp;<a href='javascript:jq_switch2Lang(\""+lmlng+"\")' STYLE='TEXT-DECORATION: NONE'>"+
			"<img src='/img/locale_"+lmlng+".png' align='middle' style='position:relative;top: -5px;'>&nbsp;"+$._b("locale_"+lmlng)+"</a>";
		}
		$('#legal_notes').html(footer_html);
	});
}

window.users_cache = {};
window.CONST_JSSTORE_BOOKMARKED = "gr_bookmrkd";
window.rqw_getcacheduser = function(user_uid)
{
	return window.users_cache[user_uid];
}

window.rqw_addcacheduser = function(user_uid,userinfo)
{
	if(user_uid){
		window.users_cache[user_uid] = userinfo;
	}
}

window.rqw_addbookmark = function()
{
	$.Storage.set(window.CONST_JSSTORE_BOOKMARKED,"1");
	$('#bmk_element').hide();
	alert(navigator.userAgent.toLowerCase().indexOf('mac') != - 1 ? $._b("Add bookmark manually Mac"):$._b("Add bookmark manually Win"));
}

window.rqw_upduserpanel = function(div_selector, focus_widget, userinfo)
{
	var divhtml = "<table width='100%' height='30px' style='background-color:black;'><tr>";
	var bmklevel = $.Storage.get(window.CONST_JSSTORE_BOOKMARKED);
	if(bmklevel != "1"){
		divhtml += "<td align='left' width='1%' valign='top'><div style='padding-top:8px;padding-left:8px;' id='bmk_element'><a href='javascript:rqw_addbookmark();'><nobr>"+$._b("Add bookmark")+"</nobr></a></td>";
	}
	divhtml += "<td align='left' width='1%' valign='top'><div style='padding-top:8px;padding-left:8px;' id='bmk_element'><a href='http://kristallum.com/get/hub'><nobr>"+$._b("News")+"</nobr></a></td>";
	divhtml += "<td align='left' width='1%' valign='top'><div style='padding-top:8px;padding-left:8px;' id='bmk_element'><a href='http://kristallum.com/get/about'><nobr>"+$._b("About")+"</nobr></a></td>";
	divhtml += "<td align='left' width='1%' valign='top'><div style='padding-top:8px;padding-left:8px;' id='bmk_element'><a href='http://kristallum.com/get/lore'><nobr>"+$._b("FAQ")+"</nobr></a></td>";
	if(userinfo != null && userinfo["u_nick"] != null){
		rqw_addcacheduser(userinfo.uid,userinfo);
		jq_payment_email = core_coalesce(userinfo.email);
		if((userinfo.u_flags & window.FLAGS_USER_SOCPRESENT) == 0){
			divhtml += "<td align='left' width='1%' valign='top'><div style='padding-top:8px;padding-left:8px;'>";
			divhtml += "<a href='javascript:jq_redirect2page({target_widget:\""+focus_widget+"\"},\"profile_edit\");'><nobr>"+$._b("Add social account here")+"</nobr></a>";
			divhtml += "&nbsp;|&nbsp;";
			divhtml += "<a href='javascript:jq_redirect2page({target_widget:\""+focus_widget+"\"},\"profile_edit\");'><nobr>"+$._b("Change avatar")+"</nobr></a>";
			divhtml += "</div></td>";
		}

		divhtml += "<td align='right' width='99%' valign='top'><div style='padding-top:8px;'>";
		divhtml += userinfo.u_nick;
		divhtml += "&nbsp;|&nbsp;";
		divhtml += "<a href='javascript:jq_redirect2page({target_widget:\""+focus_widget+"\"},\"profile_edit\");'>"+$._b("Edit profile")+"</a>";
		divhtml += "&nbsp;|&nbsp;";
		divhtml += "<a href='javascript:jq_logout_user_ask(\""+focus_widget+"\",\""+userinfo.uid+"\");'>"+$._b("Logout")+"</a>";
		divhtml += "</div></td>";
	}else{
		divhtml += "<td align='right' width='99%' valign='top'><div style='padding-top:8px;'></td>";
	}
	divhtml += "<td align='right' width='1%' valign='top'><iframe width='360px' height='30px' frameborder='0' src='/fb_like.html' scrolling='no' style='background:transparent;display:block-inline;margin-left:10px;margin-top:7px;'></iframe>";
	divhtml += "</td>";
	divhtml += "</table>";
	$(div_selector).html(divhtml);
}
