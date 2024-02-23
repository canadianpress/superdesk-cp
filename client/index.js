import {startApp} from 'superdesk-core/scripts/index';

setTimeout(() => {
    startApp(
        [            
            {
                id: 'auto-tagger',
                load: () => import('superdesk-core/scripts/extensions/auto-tagger'),
            },
            {
                id: 'translate-widget',
                load: () => import('superdesk-core/scripts/extensions/translate-widget'),
              },
            {
                id: 'planning-extension',
                load: () => import('superdesk-planning/client/planning-extension'),
                configuration: {
                    assignmentsTopBarWidget: true,
                },
            },
            {
                id: 'orangelogic-extension',
                load: () => import('./extensions/orangelogic-extension'),
            },
            {
                id: 'upload-iptc',
                load: () => import('./extensions/upload-iptc'),
            },
            {
                id: 'usage-metrics',
                load: () => import('superdesk-core/scripts/extensions/usageMetrics'),
            },
        ],
        {},
    );
});

export default angular.module('main.superdesk', []);
