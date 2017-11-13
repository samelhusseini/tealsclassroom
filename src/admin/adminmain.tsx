/// <reference path="../../localtypings/remoteclassroom.d.ts" />
/// <reference path="../../localtypings/simplewebrtc.d.ts" />

import * as React from "react";
import * as ReactDOM from "react-dom";

import { Grid, Button, Container, Segment, Menu, Icon, Header, Divider } from 'semantic-ui-react';
import { StatusFeed } from "../components/Feed";
import { UserSelector } from "../components/userselector";
import { UserDetail } from "../components/userdetail";
import { MainMenu } from "../components/MainMenu";

import { NewPostModal } from "../components/teacher/newpostmodal";

import * as SimpleWebRTC from 'simplewebrtc';

import Util from '../utils/util';

declare var Pusher: any;
declare var config: RemoteConfig;
declare var session: RemoteSession;

export interface AdminMainViewProps {
    history: any;
}
export interface AdminMainViewState {
    users: RemoteUser[];
    messages: any[];
    selectedUser?: RemoteUser;
}

export class AdminMainView extends React.Component<AdminMainViewProps, AdminMainViewState> {
    private pusher: any;
    private configChannel: any;
    private feedChannel: any;
    private messageChannel: any;
    private privateChannel: any;
    private presenceChannel: any;

    constructor(props: AdminMainViewProps) {
        super(props);
        this.state = {
            users: [],
            messages: []
        }
    }

    componentWillMount() {
        const courseId = session.course_id || '1207667';
        Pusher.logToConsole = true;
        this.pusher = new Pusher(config.PUSHER_APP_KEY, {
            encrypted: true
        });
        this.configChannel = this.pusher.subscribe('config' + courseId);
        this.feedChannel = this.pusher.subscribe('feed' + courseId);
        this.privateChannel = this.pusher.subscribe('private-ping' + courseId);
        this.presenceChannel = this.pusher.subscribe('presence-channel' + courseId);
        this.messageChannel = this.pusher.subscribe('messages' + courseId);
        this.messageChannel.bind('pusher:subscription_succeeded', this.retrieveMessageHistory, this);
    }

    componentDidMount() {
        this.feedChannel.bind('update', (data: any) => {
            //this.updateFeed();
            const studentName = data.message.fullName;
            Util.showNotification('Help needed!', `${studentName} raised his/her hand!`, data.message.avatarUrl);
        }, this);
        this.feedChannel.bind('loaded', (data: any) => {
            console.log("loaded");
        })
        this.feedChannel.bind('registered', (data: any) => {
            console.log("registered")
        })
        this.configChannel.bind('changed', (data: any) => {
            if (data.config == 'users') {
                this.updateUsers();
            }
        })
        this.messageChannel.bind('new_message', this.addMessage, this);
        this.updateUsers();

        // let webrtc = new SimpleWebRTC({
        //     localVideoEl: ReactDOM.findDOMNode((this as any).refs.local),
        //     remoteVideosEl: "",
        //     autoRequestMedia: true
        //     //url: 'https://your-production-signalserver.com/'
        // });

        // // we have to wait until it's ready
        // webrtc.on('readyToCall', function () {
        //     // you can name it anything
        //     webrtc.joinRoom(Util.getCourseId() + '8791939');
        // });
    }

    retrieveMessageHistory() {
        let self = this;
        let lastMessage = this.state.messages[this.state.messages.length - 1];
        let lastId = (lastMessage ? lastMessage.id : 0);
        const url = `/messages?after_id=${lastId}&courseId=${Util.getCourseId()}`
        fetch(url, {
            method: 'GET',
            credentials: 'include'
        })
            .then((response) => response.json())
            .then((responseJson) => {
                let messages = this.state.messages;
                responseJson.map((m: any) => { messages = messages.concat(self.addMessage(m, true)) }, self);
                messages.sort((a: any, b: any) => {
                    return (a.date > b.date) ? 1 : 0;
                });
                this.setState({ messages: messages });
            })
    }

    addMessage(message: any, skipUpdate: boolean = false) {
        if (this.messageExists(message)) {
            console.warn('Duplicate message detected');
            return;
        }
        message.read = skipUpdate || message.student == Util.getStudentId();
        if (!skipUpdate) {
            let messages = this.state.messages.concat(message);
            messages.sort((a: any, b: any) => {
                return (a.date > b.date) ? 1 : 0;
            });
            this.setState({ messages: messages });
        }
        return message;
        //$("#message-list").scrollTop($("#message-list")[0].scrollHeight);
    }

    messageExists(message: any) {
        let getId = (e: any) => { return e.id };
        let ids = this.state.messages.map(getId);
        return ids.indexOf(message.id) !== -1;
    }

    updateUsers() {
        Util.POSTCourse('/users')
            .then((response: Response) => {
                if (response.status >= 400) {
                    throw new Error("Bad response from server");
                }
                return response.json();
            })
            .then((data: any) => {
                //console.log(data);
                this.setState({ users: data });
            });
    }

    setSelectedUser(user: RemoteUser) {
        // Mark all messages as read
        const messages = this.state.messages.map((m) => {
            if (m.student == user.studentId)
                m.read = true;
        });
        this.setState({ selectedUser: user });
    }

    render() {
        const { selectedUser } = this.state;

        return <div className="pusher">
            <div className="admin-sidebar">
                <div className="admin-scrollabale">
                    <Grid>
                        <Grid.Row>
                            <Grid.Column width={12}>
                                <Header inverted as='h2'>Code Class</Header>
                            </Grid.Column>
                            <Grid.Column width={4} textAlign="left">
                                <NewPostModal trigger={<Button circular inverted color={'white' as any} icon='add' size='mini' />} />
                            </Grid.Column>
                        </Grid.Row>
                    </Grid>
                    <UserSelector messages={this.state.messages} users={this.state.users} presenceChannel={this.presenceChannel} selectedUser={selectedUser} onSelectedUser={this.setSelectedUser.bind(this)} />
                    <div className="settings">
                        <Divider inverted />
                        <Menu vertical inverted fluid borderless className="user-selector">
                            <Menu.Item >
                                <Header inverted as='h4'> <Icon inverted name='settings' />Settings </Header>
                            </Menu.Item>
                        </Menu>
                    </div>
                </div>
            </div>
            <div className="admin-body">
                <UserDetail messages={this.state.messages.filter(m => selectedUser ? m.student == selectedUser.studentId : false)} user={selectedUser} channel={this.privateChannel} />
            </div>
        </div>;
    }
}