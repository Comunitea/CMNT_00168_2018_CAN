odoo.define('theme_canilike.website_sale', function (require) {
    "use strict";

    require('web.dom_ready');
    var base = require("web_editor.base");
    var ajax = require('web.ajax');
    require("website.content.zoomodoo");

    var alert_msg = _('This address is not available for shipping from the current warehouse.');
    var alert_msg_2nd_line = _('You should check the allowed countries for this warehouse or select another warehouse.');
    var conditions = _('Check shipping info.');

    function active_addres_submit(partner_id, current_country) {
        ajax.jsonRpc("/shop/check_if_allowed_addres", 'call', {'current_country': current_country,'partner_id': partner_id})
            .then(function (data) {
                if (data) {
                    $('#address_submit').removeClass('hidden');
                    $('#alert_msg').html('');
                } else {
                    $('#address_submit').addClass('hidden');
                    $('#alert_msg').html('<div class="col-md-12"><div class="alert alert-danger"><p>'+ alert_msg +'</p><p>'+ alert_msg_2nd_line+'</p><p><a href="/shipping-info">'+conditions+'</a></p></div></div>');
                }
            });
    }

    $.when(base.ready()).then(function() {
        var allowed_shipping = $('#allowed_shipping').text() || false;
        if (allowed_shipping) {
            $('#address_submit').removeClass('hidden');
        } else {
            $('#alert_msg').html('<div class="col-md-12"><div class="alert alert-danger"><p>'+ alert_msg +'</p><p>'+ alert_msg_2nd_line+'</p><p><a href="/shipping-info">'+conditions+'</a></p></div></div>');
        }        
    });

    if(!$('.oe_website_sale').length) {
        return $.Deferred().reject("DOM doesn't contain '.oe_website_sale'");
    }

    $('.oe_website_sale').each(function () {

        $('.oe_cart').off('click','js_change_shiping').on('click', '.js_change_shipping', function() {
            if (!$('body.editor_enable').length) { //allow to edit button text with editor
                var current_country = $('#current_country').text() || false;
                var $form = $(this).parent('div.one_kanban').find('form.hide');
                var partner_id = $form.parent('div.one_kanban').find('span.js_contact').text().trim();

                if (partner_id && current_country) {
                    active_addres_submit(parseInt(partner_id), parseInt(current_country));
                }
            }
            
          });
          
    });
});