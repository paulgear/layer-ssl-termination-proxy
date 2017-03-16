import os
import charms.apt
from charms.reactive import when, when_not, set_state, remove_state
from charmhelpers.core import hookenv, host
from charms.layer.nginx import configure_site
from charmhelpers.core.hookenv import status_set, charm_dir
from charmhelpers.contrib.python.packages import pip_install
from charms.layer import lets_encrypt, lets_encrypt_nginx
from subprocess import call

config = hookenv.config()

@when_not('apt.installed.apache2-utils')
def install_utils():
	charms.apt.queue_install(['apache2-utils'])
	charms.apt.install_queued()

@when('apt.installed.apache2-utils')
@when_not('lets-encrypt-nginx.installed')
def install():
    pkgs = ['python-crontab']
    for pkg in pkgs:
        pip_install(pkg)
    set_state('lets-encrypt-nginx.installed')

@when('reverseproxy.available', 'nginx.available', 'lets-encrypt.registered', 'lets-encrypt-nginx.installed')
@when_not('lets-encrypt-nginx.running')
def set_up(reverseproxy):
    hookenv.log('Http relation found')
    services = reverseproxy.services()
    hookenv.log(services)
    live = lets_encrypt.live()
    template = 'encrypt.nginx.tmpl'
    if config['credentials']:
    	template = 'encrypt.nginx.auth.tmpl'
    configure_site('default', template, key_path=live['privkey']
                                                  , crt_path=live['fullchain']
                                                  , fqdn=config['fqdn']
                                                  , hostname=services[0][hosts][0]['hostname'])
    lets_encrypt_nginx.create_crontab()
    status_set('active', 'Ready')
    set_state('lets-encrypt-nginx.running')

@when('lets-encrypt-nginx.running')
@when_not('reverseproxy.available')
def stop_nginx():
    hookenv.log('Reverseproxy relation broken')
    if host.service_running('nginx'):
        host.service_stop('nginx')
    lets_encrypt_nginx.delete_crontab()
    remove_state('lets-encrypt-nginx.running')

@when('config.changed.credentials', 'lets-encrypt-nginx.installed')
def config_changed_credentials():
    hookenv.log('Config changed credentials')
    if config['credentials']:
    	credentials = config['credentials'].split(' ')
	    if os.path.exists('/etc/nginx/.htpasswd'):
	    	call(['htpasswd', '-c', '/etc/nginx/.htpasswd', credentials[0], credentials[1]])
	    else:
	    	call(['htpasswd', '/etc/nginx/.htpasswd', credentials[0], credentials[1]])
	else:
		os.remove('/etc/nginx/.htpasswd')
    remove_state('kafkasubscriber.running')