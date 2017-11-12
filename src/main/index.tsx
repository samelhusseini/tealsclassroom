/// <reference path="../../localtypings/remoteclassroom.d.ts" />
/// <reference path="../../localtypings/simplewebrtc.d.ts" />

import * as React from "react";
import * as ReactDOM from "react-dom";

import * as SimpleWebRTC from 'simplewebrtc';

import { Menu, Button, Icon } from "semantic-ui-react";

import Util from '../utils/util';

import { NotificationModal } from "../components/student/notificationmodal";
import { Frame } from "../components/student/frame";
import { Messages } from "../components/student/messages";

declare var Pusher: any;
declare var config: RemoteConfig;
declare var session: RemoteSession;

export interface MainAppProps {
}

export interface MainAppState {
    iframeUrl?: string;
    sidebarOpen?: boolean;
}

export class MainApp extends React.Component<MainAppProps, MainAppState> {
    private pusher: any;
    private configChannel: any;
    private pingChannel: any;

    constructor(props: MainAppProps) {
        super(props);
        this.state = {
            iframeUrl: config.iframeUrl
        }

        this.handleNeedHelp = this.handleNeedHelp.bind(this);
        this.handleStartCall = this.handleStartCall.bind(this);
    }

    componentWillMount() {
        const courseId = Util.getCourseId();
        Pusher.logToConsole = true;
        this.pusher = new Pusher(config.PUSHER_APP_KEY, {
            encrypted: true
        });
        this.configChannel = this.pusher.subscribe('config' + courseId);
        this.pingChannel = this.pusher.subscribe('private-ping' + courseId);
    }

    componentDidMount() {
        this.configChannel.bind('changed', (config: any) => {
            const newState: MainAppState = {};
            if (this.state.iframeUrl !== config.iframeUrl) {
                newState.iframeUrl = config.iframeUrl;
            }
            if (Object.keys(newState).length > 0) this.setState(newState);
        }, this);
        this.pingChannel.bind('client-ping' + Util.getCourseId(), (data: any) => {
            if (data.studentId == Util.getStudentId()) {
                Util.showNotification('Ping! Headphones On!', `Teacher is trying to contact you!`, '/public/images/notification/headphones.png');
            }
        })
        window.addEventListener('message', (e: any) => {
            const snapData = e.data;
            if (snapData && snapData.action && snapData.action == "save") {
                const projectName = snapData.name;
                location.hash = 'courseId=' +
                    encodeURIComponent(Util.getCourseId()) +
                    '&studentId=' +
                    encodeURIComponent(Util.getStudentId()) +
                    '&projectName=' +
                    encodeURIComponent(projectName);
            }
        }, false);

        // let webrtc = new SimpleWebRTC({
        //     localVideoEl: "",
        //     remoteVideosEl: "",
        //     autoRequestMedia: true,
        //     media: { audio: true, video: false, screen: true }
        //     //url: 'https://your-production-signalserver.com/'
        // });

        // // we have to wait until it's ready
        // webrtc.on('readyToCall', function () {
        //     // you can name it anything
        //     webrtc.joinRoom(Util.getCourseId() + Util.getStudentId());

        //     webrtc.shareScreen(function (err: any) {
        //         if (err) {
        //             console.log(err);
        //         } else {
        //             console.log("Sharing screen");
        //         }
        //     });
        // });
    }

    handleStartCall(e: any) {
        Util.POSTUser('/register');
        if (session.remote_link) {
            window.open(session.remote_link + "?sl=");
        }
    }

    handleNeedHelp(e: any) {
        Util.POST('/help', {
            studentId: Util.getStudentId(),
            courseId: Util.getCourseId(),
            studentName: session.full_name || 'Unknown Name'
        });
    }

    handleOpenSidebar(e: any) {
        this.setState({ sidebarOpen: !this.state.sidebarOpen })
    }

    render() {
        const { iframeUrl, sidebarOpen } = this.state;
        const { full_name, user_image, remote_link } = session;

        if (window.location.hash && Util.isInstructor()) {
            // Redirect to SNAP present
            const hash2Obj = window.location.hash.substr(1)
                .split("&")
                .map(el => el.split("="))
                .reduce((pre: any, cur: any) => { pre[cur[0]] = cur[1]; return pre; }, {});
            if (hash2Obj['courseId'] && hash2Obj['studentId'] && hash2Obj['projectName']) {
                window.location.href = `/public/SNAP/snap.html#present:Username=${hash2Obj['courseId'] + hash2Obj['studentId']}&ProjectName=${hash2Obj['projectName']}`;
            } else {
                window.location.href = `/admin`
            }
        }

        const snapUrl = `/public/SNAP/snap.html#login:${Util.getCourseId() + Util.getStudentId()}`;
        return <div className="pusher">
            <div className={`main-body ${sidebarOpen ? 'sidebar-visible' : ''}`}>
                <Menu inverted borderless className="starter-menu" size='mini'>
                    <Menu.Menu position='left'>
                        <Menu.Item>
                            <img className="ui avatar image" src={user_image} />
                            <span>{full_name}</span>
                        </Menu.Item>
                    </Menu.Menu>
                    {remote_link ?
                        <Menu.Item>
                            <Button color="green" icon labelPosition='left' onClick={this.handleStartCall}><Icon name='call' /> Start Call</Button>
                        </Menu.Item> : undefined}
                    <Menu.Item>
                        <Button color="blue" icon labelPosition='left' onClick={this.handleNeedHelp}><Icon name='hand pointer' />Raise Hand</Button>
                    </Menu.Item>
                    <Menu.Item>
                        <Button color="blue" icon labelPosition='left' onClick={this.handleOpenSidebar.bind(this)}><Icon name='hand pointer' />Open Sidebar</Button>
                    </Menu.Item>
                    <Menu.Menu position='right'>
                    </Menu.Menu>
                </Menu>
                <div className="frame-body">
                    <Frame url={snapUrl} />
                </div>
            </div>
            <div className={`main-sidebar ${sidebarOpen ? 'sidebar-visible' : ''}`}>
                <Messages />
            </div>
            <NotificationModal open={false} />
        </div>;
    }
}

ReactDOM.render(
    <MainApp />,
    document.getElementById("root")
);