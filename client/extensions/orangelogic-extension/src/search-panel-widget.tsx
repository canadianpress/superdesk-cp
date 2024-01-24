import * as React from 'react';
import {ISearchPanelWidgetProps, ISuperdesk} from 'superdesk-api';

type IMediaType = 'Image' | 'Video';

interface IParams {
    from: string;
    to: string;
    mediaTypes: {
        [key in IMediaType]?: boolean;
    };
};

interface IMediaTypeLabel {
    type: IMediaType,
    label: string;
}

export const searchPanelWidgetFactory = (
    gettext: ISuperdesk['localization']['gettext'],
): React.ComponentType<ISearchPanelWidgetProps<unknown>> => {
    const mediaTypes: Array<IMediaTypeLabel> = [
        {
            type: 'Image',
            label: gettext('Picture'),
        },
        {
            type: 'Video',
            label: gettext('Video'),
        },
    ];

    class SearchPanelWidget extends React.PureComponent<ISearchPanelWidgetProps<IParams>> {
        toggleMediaType(type: IMediaType) {
            const mediaTypes = this.props.params.mediaTypes || {};

            mediaTypes[type] = !mediaTypes[type];
            this.props.setParams({mediaTypes});
        }

        isActive(type: IMediaType) {
            return this.props.params.mediaTypes != null && this.props.params.mediaTypes[type] === true;
        }

        render() {
            const {params} = this.props;

            if (this.props.provider !== 'orangelogic') {
                return null;
            }

            return (
                <fieldset>
                    <div className="field">
                        <label className="search-label"></label>
                        {mediaTypes.map((type) => (
                            <button key={type.type}
                                className={'btn btn--primary' + (this.isActive(type.type) ? ' btn--active' : '')}
                                onClick={() => this.toggleMediaType(type.type)}
                            >{type.label}</button>
                        ))}
                    </div>
                    <div className="field">
                        <label className="search-label">{gettext('From')}</label>
                        <input type="date" value={params.from || ''}
                            onChange={(event) => this.props.setParams({from: event.target.value})}
                        />
                    </div>
                    <div className="field">
                        <label className="search-label">{gettext('To')}</label>
                        <input type="date" value={params.to || ''}
                            onChange={(event) => this.props.setParams({to: event.target.value})}
                        />
                    </div>
                </fieldset>
            );
        }
    };

    // casting is required because of limitations on use of generics in superdesk-api
    return SearchPanelWidget as React.ComponentType<ISearchPanelWidgetProps<unknown>>;
};