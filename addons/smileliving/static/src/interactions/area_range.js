import { Interaction } from '@web/public/interaction';
import { redirect } from '@web/core/utils/urls';
import { registry } from '@web/core/registry';

export class AreaRange extends Interaction {
    static selector = '#smileliving_area_range_option';
    dynamicContent = {
        'input[type="range"]': { 't-on-newRangeValue': this.onAreaRangeSelected },
    };

    /**
     * @param {Event} ev
     */
    onAreaRangeSelected(ev) {
        const range = ev.currentTarget;
        const url = new URL(range.dataset.url, window.location.origin);
        const searchParams = url.searchParams;

        if (parseFloat(range.min) !== range.valueLow) {
            searchParams.set('filter_area_min', range.valueLow);
        }
        if (parseFloat(range.max) !== range.valueHigh) {
            searchParams.set('filter_area_max', range.valueHigh);
        }

        const product_list_div = document.querySelector('.o_wsale_products_grid_table_wrapper');
        if (product_list_div) {
            product_list_div.classList.add('opacity-50');
        }
        redirect(`${url.pathname}?${searchParams.toString()}`);
    }
}

registry
    .category('public.interactions')
    .add('smileliving.area_range', AreaRange);
